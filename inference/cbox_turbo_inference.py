import onnxruntime
from huggingface_hub import hf_hub_download
import numpy as np
from tqdm import trange
import librosa
import soundfile as sf
import os

MODEL_ID = "ResembleAI/chatterbox-turbo-ONNX"
SAMPLE_RATE = 24000
START_SPEECH_TOKEN = 6561
STOP_SPEECH_TOKEN = 6562
SILENCE_TOKEN = 4299
NUM_KV_HEADS = 16
HEAD_DIM = 64


class RepetitionPenaltyLogitsProcessor:
    def __init__(self, penalty: float):
        if not isinstance(penalty, float) or not (penalty > 0):
            raise ValueError(
                f"`penalty` must be a strictly positive float, but is {penalty}"
            )
        self.penalty = penalty

    def __call__(self, input_ids: np.ndarray, scores: np.ndarray) -> np.ndarray:
        score = np.take_along_axis(scores, input_ids, axis=1)
        score = np.where(score < 0, score * self.penalty, score / self.penalty)
        scores_processed = scores.copy()
        np.put_along_axis(scores_processed, input_ids, score, axis=1)
        return scores_processed


def load_cbox_turbo_model(model_path=None):
    """Load the cbox_turbo ONNX models from local path or download from HuggingFace"""
    if model_path is None:
        model_path = os.path.join(
            os.path.dirname(__file__), "..", "models", "cbox_turbo"
        )

    if os.path.exists(model_path):
        # Load from local path
        onnx_dir = os.path.join(model_path, "onnx")
        conditional_decoder_path = os.path.join(
            onnx_dir, "conditional_decoder_q4f16.onnx"
        )
        speech_encoder_path = os.path.join(onnx_dir, "speech_encoder_q4f16.onnx")
        embed_tokens_path = os.path.join(onnx_dir, "embed_tokens_q4f16.onnx")
        language_model_path = os.path.join(onnx_dir, "language_model_q4f16.onnx")

        # Check if data files exist, if not, skip them (some models may have weights embedded)
        def create_session_with_fallback(model_path):
            """Create ONNX session, handling missing data files gracefully"""
            try:
                return onnxruntime.InferenceSession(model_path)
            except Exception as e:
                if "filesystem error" in str(e) and "_data" in str(e):
                    # Try without expecting external data
                    import onnx

                    model = onnx.load(model_path)
                    # Check if model has external data
                    if not any(
                        hasattr(tensor, "external_data") and tensor.external_data
                        for tensor in model.graph.initializer
                    ):
                        # Model doesn't actually need external data, try loading again
                        return onnxruntime.InferenceSession(
                            model_path, providers=["CPUExecutionProvider"]
                        )
                raise e

        speech_encoder_session = create_session_with_fallback(speech_encoder_path)
        embed_tokens_session = create_session_with_fallback(embed_tokens_path)
        language_model_session = create_session_with_fallback(language_model_path)
        cond_decoder_session = create_session_with_fallback(conditional_decoder_path)

    else:
        # Download from HuggingFace
        def download_model(name: str, dtype: str = "q4f16") -> str:
            filename = f"{name}{'' if dtype == 'fp32' else '_quantized' if dtype == 'q8' else f'_{dtype}'}.onnx"
            graph = hf_hub_download(MODEL_ID, subfolder="onnx", filename=filename)
            try:
                hf_hub_download(MODEL_ID, subfolder="onnx", filename=f"{filename}_data")
            except Exception:
                # Data file might not exist for some models
                pass
            return graph

        conditional_decoder_path = download_model("conditional_decoder", dtype="q4f16")
        speech_encoder_path = download_model("speech_encoder", dtype="q4f16")
        embed_tokens_path = download_model("embed_tokens", dtype="q4f16")
        language_model_path = download_model("language_model", dtype="q4f16")

        # Create ONNX sessions
        speech_encoder_session = onnxruntime.InferenceSession(speech_encoder_path)
        embed_tokens_session = onnxruntime.InferenceSession(embed_tokens_path)
        language_model_session = onnxruntime.InferenceSession(language_model_path)
        cond_decoder_session = onnxruntime.InferenceSession(conditional_decoder_path)

    return {
        "speech_encoder": speech_encoder_session,
        "embed_tokens": embed_tokens_session,
        "language_model": language_model_session,
        "cond_decoder": cond_decoder_session,
    }


def generate_speech(
    text,
    target_voice_path,
    output_file_name,
    max_new_tokens=1024,
    repetition_penalty=1.2,
    apply_watermark=False,
):
    """Generate speech using the cbox_turbo model"""
    # Import transformers only when needed to avoid slow startup
    from transformers import AutoTokenizer
    
    # Load models
    sessions = load_cbox_turbo_model()
    speech_encoder_session = sessions["speech_encoder"]
    embed_tokens_session = sessions["embed_tokens"]
    language_model_session = sessions["language_model"]
    cond_decoder_session = sessions["cond_decoder"]

    # Prepare audio input
    audio_values, _ = librosa.load(target_voice_path, sr=SAMPLE_RATE)
    audio_values = audio_values[np.newaxis, :].astype(np.float32)

    # Prepare text input
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    input_ids = tokenizer(text, return_tensors="np")["input_ids"].astype(np.int64)

    # Generation loop
    repetition_penalty_processor = RepetitionPenaltyLogitsProcessor(
        penalty=repetition_penalty
    )
    generate_tokens = np.array([[START_SPEECH_TOKEN]], dtype=np.int64)

    for i in trange(max_new_tokens, desc="Sampling", dynamic_ncols=True):
        inputs_embeds = embed_tokens_session.run(None, {"input_ids": input_ids})[0]

        if i == 0:
            ort_speech_encoder_input = {"audio_values": audio_values}
            cond_emb, prompt_token, speaker_embeddings, speaker_features = (
                speech_encoder_session.run(None, ort_speech_encoder_input)
            )
            inputs_embeds = np.concatenate((cond_emb, inputs_embeds), axis=1)

            # Initialize cache and LLM inputs
            batch_size, seq_len, _ = inputs_embeds.shape
            past_key_values = {
                i.name: np.zeros(
                    [batch_size, NUM_KV_HEADS, 0, HEAD_DIM],
                    dtype=np.float16 if i.type == "tensor(float16)" else np.float32,
                )
                for i in language_model_session.get_inputs()
                if "past_key_values" in i.name
            }
            attention_mask = np.ones((batch_size, seq_len), dtype=np.int64)
            position_ids = (
                np.arange(seq_len, dtype=np.int64)
                .reshape(1, -1)
                .repeat(batch_size, axis=0)
            )

        logits, *present_key_values = language_model_session.run(
            None,
            dict(
                inputs_embeds=inputs_embeds,
                attention_mask=attention_mask,
                position_ids=position_ids,
                **past_key_values,
            ),
        )

        logits = logits[:, -1, :]
        next_token_logits = repetition_penalty_processor(generate_tokens, logits)

        input_ids = np.argmax(next_token_logits, axis=-1, keepdims=True).astype(
            np.int64
        )
        generate_tokens = np.concatenate((generate_tokens, input_ids), axis=-1)
        if (input_ids.flatten() == STOP_SPEECH_TOKEN).all():
            break

        # Update values for next generation loop
        attention_mask = np.concatenate(
            [attention_mask, np.ones((batch_size, 1), dtype=np.int64)], axis=1
        )
        position_ids = position_ids[:, -1:] + 1
        for j, key in enumerate(past_key_values):
            past_key_values[key] = present_key_values[j]

    # Decode audio
    speech_tokens = generate_tokens[:, 1:-1]
    silence_tokens = np.full(
        (speech_tokens.shape[0], 3), SILENCE_TOKEN, dtype=np.int64
    )  # Add silence at the end
    speech_tokens = np.concatenate(
        [prompt_token, speech_tokens, silence_tokens], axis=1
    )

    wav = cond_decoder_session.run(
        None,
        dict(
            speech_tokens=speech_tokens,
            speaker_embeddings=speaker_embeddings,
            speaker_features=speaker_features,
        ),
    )[0].squeeze(axis=0)

    # Optional: Apply watermark
    if apply_watermark:
        try:
            import perth

            watermarker = perth.PerthImplicitWatermarker()
            wav = watermarker.apply_watermark(wav, sample_rate=SAMPLE_RATE)
        except ImportError:
            print("Warning: perth module not available, skipping watermark")

    sf.write(output_file_name, wav, SAMPLE_RATE)
    return output_file_name
