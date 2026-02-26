"""
Canary 1B v2 - Lean AED Inference

Based on onnx-asr NemoConformerAED implementation.
Autoregressive encoder-decoder with growing decoder_mems.

25 languages, punctuation/casing control, translation.
"""
import numpy as np
import onnxruntime as rt
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TranscriptionResult:
    """Result with tokens and optional logprobs."""
    text: str
    tokens: List[int]
    logprobs: Optional[List[float]] = None


class Canary1Bv2:
    """
    Canary 1B v2 via onnx-asr ONNX export.
    
    Model structure:
    - encoder-model.onnx: audio features → encoder_embeddings + encoder_mask
    - decoder-model.onnx: autoregressive with growing decoder_mems
    
    Key difference from 180m-Flash:
    - Uses unified decoder_mems that grows each step
    - 25 European languages
    - 16,384 vocab size
    """
    
    SAMPLE_RATE = 16000
    FEATURES_SIZE = 128  # Canary uses 128-dim mel
    SUBSAMPLING_FACTOR = 8
    MAX_SEQUENCE_LENGTH = 1024
    
    def __init__(self, model_dir: Path, provider: str = "cuda"):
        model_dir = Path(model_dir)
        
        # Select providers with CUDA config
        if provider == "cuda":
            providers = [
                ('CUDAExecutionProvider', {
                    'device_id': 0,
                    'arena_extend_strategy': 'kNextPowerOfTwo',
                    'cudnn_conv_algo_search': 'EXHAUSTIVE',
                    'do_copy_in_default_stream': True,
                }),
                'CPUExecutionProvider'
            ]
            # Enable CUDA graph for better performance
            cuda_opts = rt.SessionOptions()
            cuda_opts.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_ALL
            cuda_opts.enable_mem_pattern = True
            cuda_opts.enable_cpu_mem_arena = False
        else:
            providers = ['CPUExecutionProvider']
            cuda_opts = rt.SessionOptions()
            cuda_opts.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Load encoder
        encoder_path = model_dir / "encoder.int8.onnx"
        if not encoder_path.exists():
            encoder_path = model_dir / "encoder-model.int8.onnx"
        if not encoder_path.exists():
            encoder_path = model_dir / "encoder-model.onnx"
        self.encoder = rt.InferenceSession(str(encoder_path), cuda_opts, providers=providers)
        
        # Load decoder
        decoder_path = model_dir / "decoder.int8.onnx"
        if not decoder_path.exists():
            decoder_path = model_dir / "decoder-model.int8.onnx"
        if not decoder_path.exists():
            decoder_path = model_dir / "decoder-model.onnx"
        self.decoder = rt.InferenceSession(str(decoder_path), cuda_opts, providers=providers)
        

        
        # Load vocab
        self.vocab = {}  # id -> token
        self.tokens = {}  # token -> id
        with open(model_dir / "vocab.txt", 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(' ')
                if len(parts) >= 2:
                    token = ' '.join(parts[:-1])
                    idx = int(parts[-1])
                    self.vocab[idx] = token
                    self.tokens[token] = idx
        
        self.vocab_size = len(self.vocab)
        self.eos_token_id = self.tokens.get("<|endoftext|>", 3)
        
        # Get decoder_mems shape from decoder inputs
        self._decoder_mems_shape = None
        for inp in self.decoder.get_inputs():
            if inp.name == "decoder_mems":
                self._decoder_mems_shape = inp.shape
                break
    
    def _compute_features(self, audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Compute 128-dim log-mel spectrogram features.
        
        Args:
            audio: float32 [samples] or [batch, samples], 16kHz mono
            
        Returns:
            features: [batch, feat_dim, time]
            lengths: [batch]
        """
        import torchaudio
        import torch
        
        if audio.ndim == 1:
            audio = audio[np.newaxis, :]
        
        audio = audio.astype(np.float32)
        audio_t = torch.from_numpy(audio)
        
        # NeMo params: n_fft=512, hop=160, win=400, n_mels=128
        mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=self.SAMPLE_RATE,
            n_fft=512,
            win_length=400,
            hop_length=160,
            n_mels=self.FEATURES_SIZE,
            norm='slaney',
            mel_scale='slaney',
        )
        
        mel = mel_transform(audio_t)  # [batch, n_mels, time]
        log_mel = torch.log(mel + 1e-10)
        
        # Per-feature normalization
        mean = log_mel.mean(dim=-1, keepdim=True)
        std = log_mel.std(dim=-1, keepdim=True)
        log_mel = (log_mel - mean) / (std + 1e-5)
        
        features = log_mel.numpy().astype(np.float32)
        lengths = np.array([features.shape[2]], dtype=np.int64)
        
        return features, lengths
    
    def _get_prompt_tokens(
        self, 
        language: str = "en",
        target_language: Optional[str] = None,
        pnc: bool = True
    ) -> np.ndarray:
        """Build decoder prompt sequence."""
        target_language = target_language or language
        pnc_token = "<|pnc|>" if pnc else "<|nopnc|>"
        
        prompt = [
            self.tokens.get("<|startofcontext|>", 7),
            self.tokens.get("<|startoftranscript|>", 4),
            self.tokens.get("<|emo:undefined|>", self.tokens.get("<|emo_undefined|>", 16)),
            self.tokens.get(f"<|{language}|>", self.tokens.get("<|en|>", 62)),
            self.tokens.get(f"<|{target_language}|>", self.tokens.get("<|en|>", 62)),
            self.tokens.get(pnc_token, 5 if pnc else 6),
            self.tokens.get("<|noitn|>", 9),
            self.tokens.get("<|notimestamp|>", 11),
            self.tokens.get("<|nodiarize|>", 13),
        ]
        
        return np.array([prompt], dtype=np.int64)
    
    def _run_encoder(
        self, 
        features: np.ndarray, 
        lengths: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Run encoder on mel features."""
        encoder_embeddings, encoder_mask = self.encoder.run(
            ["encoder_embeddings", "encoder_mask"],
            {"audio_signal": features, "length": lengths}
        )
        return encoder_embeddings, encoder_mask
    
    def _run_decoder(
        self,
        input_ids: np.ndarray,
        encoder_embeddings: np.ndarray,
        encoder_mask: np.ndarray,
        decoder_mems: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Run one decoder step."""
        # If we have accumulated mems, only pass the last token
        if decoder_mems.shape[2] > 0:
            input_ids = input_ids[:, -1:]
        
        logits, decoder_hidden_states = self.decoder.run(
            ["logits", "decoder_hidden_states"],
            {
                "input_ids": input_ids,
                "encoder_embeddings": encoder_embeddings,
                "encoder_mask": encoder_mask,
                "decoder_mems": decoder_mems,
            }
        )
        return logits, decoder_hidden_states
    
    def _decode_autoregressive(
        self,
        encoder_embeddings: np.ndarray,
        encoder_mask: np.ndarray,
        language: str = "en",
        target_language: Optional[str] = None,
        pnc: bool = True,
    ) -> TranscriptionResult:
        """
        Autoregressive decoding with growing decoder_mems.
        """
        batch_size = encoder_embeddings.shape[0]
        batch_tokens = self._get_prompt_tokens(language, target_language, pnc)
        batch_tokens = np.repeat(batch_tokens, batch_size, axis=0)
        prefix_len = batch_tokens.shape[1]
        
        # Initialize empty decoder_mems
        # Shape: [num_layers, batch, 0, hidden_dim]
        if self._decoder_mems_shape:
            num_layers = self._decoder_mems_shape[0]
            hidden_dim = self._decoder_mems_shape[3]
        else:
            num_layers = 8  # Canary 1B v2 default
            hidden_dim = 1024
        
        decoder_mems = np.empty((num_layers, batch_size, 0, hidden_dim), dtype=np.float32)
        batch_logprobs = np.zeros((batch_size, 0), dtype=np.float32)
        
        while batch_tokens.shape[1] < self.MAX_SEQUENCE_LENGTH:
            logits, decoder_mems = self._run_decoder(
                batch_tokens, encoder_embeddings, encoder_mask, decoder_mems
            )
            
            # Greedy: argmax of last position
            next_tokens = np.argmax(logits[:, -1], axis=-1)
            
            # Check for EOS
            if (next_tokens == self.eos_token_id).all():
                break
            
            # Get logprobs for the chosen tokens
            next_logprobs = np.take_along_axis(
                logits[:, -1], 
                next_tokens[:, None], 
                axis=-1
            ).squeeze(axis=-1)
            
            # Append token
            batch_tokens = np.concatenate(
                (batch_tokens, next_tokens[:, None]), 
                axis=-1
            )
            batch_logprobs = np.concatenate(
                (batch_logprobs, next_logprobs[:, None]), 
                axis=-1
            )
        
        # Extract output tokens (skip prompt, filter special tokens)
        output_tokens = []
        for t in batch_tokens[0, prefix_len:]:
            t = int(t)
            if t == self.eos_token_id:
                break
            token_str = self.vocab.get(t, '')
            if not token_str.startswith('<|'):
                output_tokens.append(t)
        
        # Decode to text
        text_parts = []
        for t in output_tokens:
            token_str = self.vocab.get(t, '')
            # SentencePiece underscore → space
            token_str = token_str.replace('▁', ' ')
            text_parts.append(token_str)
        
        text = ''.join(text_parts).strip()
        
        return TranscriptionResult(
            text=text,
            tokens=output_tokens,
            logprobs=batch_logprobs[0].tolist() if len(batch_logprobs) > 0 else None
        )
    
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: str = "en",
        target_language: Optional[str] = None,
        pnc: bool = True,
    ) -> str:
        """
        Transcribe or translate audio to text.
        
        Args:
            audio: float32 mono audio
            sample_rate: input sample rate (resampled to 16kHz if needed)
            language: source language (en, de, es, fr, etc - 25 languages)
            target_language: target language (same as source for transcription)
            pnc: enable punctuation and casing
            
        Returns:
            Transcribed/translated text
        """
        # Resample if needed
        if sample_rate != self.SAMPLE_RATE:
            import torchaudio
            import torch
            audio_t = torch.from_numpy(audio).unsqueeze(0)
            audio_t = torchaudio.functional.resample(audio_t, sample_rate, self.SAMPLE_RATE)
            audio = audio_t.squeeze(0).numpy()
        
        # Compute features
        features, lengths = self._compute_features(audio)
        
        # Run encoder
        encoder_embeddings, encoder_mask = self._run_encoder(features, lengths)
        
        # Decode
        result = self._decode_autoregressive(
            encoder_embeddings, encoder_mask, language, target_language, pnc
        )
        
        return result.text


def load_canary_1b_v2(model_dir: Path = None, provider: str = "cuda") -> Canary1Bv2:
    """Factory function to load the default Canary 1B v2 model."""
    if model_dir is None:
        model_dir = Path(__file__).parent.parent / "models" / "canary1b"
    return Canary1Bv2(model_dir, provider)
