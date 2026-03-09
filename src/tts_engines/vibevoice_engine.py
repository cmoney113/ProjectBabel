"""
VibeVoice Engine - Using Microsoft VibeVoice-Realtime for streaming TTS
Supports ~300ms first audio latency with streaming text input
"""

import sys
import copy
import warnings
import numpy as np
import soundfile as sf
import torch
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import threading

logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings("ignore")

# Suppress PyTorch warnings about uninitialized weights
torch_logger = logging.getLogger("torch")
torch_logger.setLevel(logging.ERROR)

# Suppress transformers logger for tokenizer mismatch warnings
transformers_logger = logging.getLogger("transformers")
transformers_logger.setLevel(logging.ERROR)

# Add VibeVoice to path
VIBEVOCE_PATH = Path("/home/craig/new-projects/voice_ai/inference/VibeVoice-main")
if str(VIBEVOCE_PATH) not in sys.path:
    sys.path.insert(0, str(VIBEVOCE_PATH))


class VibeVoiceEngine:
    """VibeVoice Realtime TTS engine with streaming support"""

    def __init__(self, model_path: str = None, device: str = "cuda"):
        """Initialize VibeVoice engine

        Args:
            model_path: Path to VibeVoice model (defaults to local model)
            device: Device to run on ('cuda' or 'cpu')
        """
        # Default paths
        base_path = Path("/home/craig/new-projects/voice_ai/models")

        if model_path is None:
            model_path = base_path / "VibeVoiceRealtime05b"
        self.model_path = Path(model_path)

        self.device = device
        self.processor = None
        self.model = None
        self.voice_presets: Dict[str, Path] = {}
        self.default_voice_key: Optional[str] = None
        self._voice_cache: Dict[str, Any] = {}

        # Mapping from short voice names to full voice keys
        self._voice_name_mapping = {
            "Carter": "en-Carter_man",
            "Emma": "en-Emma_woman",
            "Davis": "en-Davis_man",
            "Frank": "en-Frank_man",
            "Grace": "en-Grace_woman",
            "Mike": "en-Mike_man",
        }

        # Inference settings
        self.inference_steps = 5
        self.sample_rate = 24000

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model directory not found: {self.model_path}")

        self._load_voice_presets()

    def _load_voice_presets(self):
        """Load available voice presets"""
        voices_dir = self.model_path / "voices" / "streaming_model"
        if not voices_dir.exists():
            # Try alternative path
            voices_dir = self.model_path / "voices"

        if not voices_dir.exists():
            logger.warning(f"Voices directory not found: {voices_dir}")
            return

        self.voice_presets = {}
        for pt_path in voices_dir.rglob("*.pt"):
            self.voice_presets[pt_path.stem] = pt_path

        # Set default voice
        default_keys = ["en-Carter_man", "Carter", "Emma"]
        for key in default_keys:
            if key in self.voice_presets:
                self.default_voice_key = key
                break

        if not self.default_voice_key and self.voice_presets:
            self.default_voice_key = next(iter(self.voice_presets))

        logger.info(f"VibeVoice loaded {len(self.voice_presets)} voice presets")

    def load(self):
        """Load the VibeVoice model and processor"""
        import torch

        from vibevoice.modular.modeling_vibevoice_streaming_inference import (
            VibeVoiceStreamingForConditionalGenerationInference,
        )
        from vibevoice.processor.vibevoice_streaming_processor import (
            VibeVoiceStreamingProcessor,
        )

        logger.info(f"Loading VibeVoice processor from {self.model_path}")
        self.processor = VibeVoiceStreamingProcessor.from_pretrained(
            str(self.model_path)
        )

        # Determine dtype and attention implementation
        if self.device == "mps":
            load_dtype = torch.float32
            device_map = None
            attn_impl = "sdpa"
        elif self.device == "cuda":
            load_dtype = torch.bfloat16
            device_map = "cuda"
            attn_impl = "flash_attention_2"
        else:
            load_dtype = torch.float32
            device_map = self.device
            attn_impl = "sdpa"

        logger.info(
            f"Loading VibeVoice model: device={self.device}, dtype={load_dtype}, attn={attn_impl}"
        )

        try:
            self.model = (
                VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                    str(self.model_path),
                    torch_dtype=load_dtype,
                    device_map=device_map,
                    attn_implementation=attn_impl,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to load with {attn_impl}, trying SDPA: {e}")
            self.model = (
                VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                    str(self.model_path),
                    torch_dtype=load_dtype,
                    device_map=device_map,
                    attn_implementation="sdpa",
                )
            )

        self.model.eval()

        # Configure noise scheduler
        self.model.model.noise_scheduler = self.model.model.noise_scheduler.from_config(
            self.model.model.noise_scheduler.config,
            algorithm_type="sde-dpmsolver++",
            beta_schedule="squaredcos_cap_v2",
        )
        self.model.set_ddpm_inference_steps(num_steps=self.inference_steps)

        logger.info("VibeVoice model loaded successfully")

    def _ensure_voice_cached(self, key: str):
        """Ensure voice preset is cached"""
        import torch

        # Map short name to full name if needed
        if key not in self.voice_presets:
            if key in self._voice_name_mapping:
                key = self._voice_name_mapping[key]

        if key not in self.voice_presets:
            available = ", ".join(self.voice_presets.keys()) or "none"
            raise RuntimeError(
                f"Voice preset '{key}' not found. Available: {available}"
            )

        if key not in self._voice_cache:
            preset_path = self.voice_presets[key]
            logger.info(f"Loading voice preset: {key} from {preset_path}")
            prefilled_outputs = torch.load(
                preset_path,
                map_location=self.device,
                weights_only=False,
            )
            self._voice_cache[key] = prefilled_outputs

        return self._voice_cache[key]

    def _prepare_inputs(self, text: str, prefilled_outputs):
        """Prepare model inputs"""
        if not self.processor or not self.model:
            raise RuntimeError("VibeVoice model not loaded")

        import torch

        text = text.replace("'", "'").strip()

        processor_kwargs = {
            "text": text,
            "cached_prompt": prefilled_outputs,
            "padding": True,
            "return_tensors": "pt",
            "return_attention_mask": True,
        }

        processed = self.processor.process_input_with_cached_prompt(**processor_kwargs)

        torch_device = torch.device(self.device)
        prepared = {
            key: value.to(torch_device) if hasattr(value, "to") else value
            for key, value in processed.items()
        }
        return prepared

    def synthesize(
        self,
        text: str,
        voice: str = None,
        cfg_scale: float = 1.5,
        temperature: float = 0.9,
        top_p: float = 0.9,
        do_sample: bool = False,
        streaming: bool = False,
    ):
        """Synthesize speech from text

        Args:
            text: Input text to synthesize
            voice: Voice name (default, Carter, Emma, etc.)
            cfg_scale: Classifier-free guidance scale
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            do_sample: Whether to use sampling
            streaming: If True, yield audio chunks (not implemented for batch)

        Returns:
            Audio data as numpy array at 24kHz sample rate
        """
        if self.model is None:
            self.load()

        # Get voice
        if voice is None:
            voice = self.default_voice_key
        if voice is None:
            voice = "Carter"

        prefilled_outputs = self._ensure_voice_cached(voice)

        # Prepare inputs
        inputs = self._prepare_inputs(text, prefilled_outputs)

        # Generate
        try:
            from vibevoice.modular.streamer import AudioStreamer

            # Use streaming for batch too - it yields chunks
            audio_streamer = AudioStreamer(batch_size=1, stop_signal=None, timeout=None)
            stop_signal = threading.Event()

            # Run generation in thread
            def run_generation():
                try:
                    self.model.generate(
                        **inputs,
                        max_new_tokens=None,
                        cfg_scale=cfg_scale,
                        tokenizer=self.processor.tokenizer,
                        generation_config={
                            "do_sample": do_sample,
                            "temperature": temperature if do_sample else 1.0,
                            "top_p": top_p if do_sample else 1.0,
                        },
                        audio_streamer=audio_streamer,
                        stop_check_fn=stop_signal.is_set,
                        verbose=False,
                        refresh_negative=True,
                        all_prefilled_outputs=copy.deepcopy(prefilled_outputs),
                    )
                except Exception as e:
                    logger.error(f"Generation error: {e}")
                    audio_streamer.end()

            thread = threading.Thread(target=run_generation, daemon=True)
            thread.start()

            # Collect all audio chunks
            all_audio = []
            try:
                stream = audio_streamer.get_stream(0)
                for audio_chunk in stream:
                    if hasattr(audio_chunk, "detach"):
                        audio_chunk = (
                            audio_chunk.detach().cpu().to(torch.float32).numpy()
                        )
                    else:
                        audio_chunk = np.asarray(audio_chunk, dtype=np.float32)

                    if audio_chunk.ndim > 1:
                        audio_chunk = audio_chunk.reshape(-1)

                    # Normalize
                    peak = np.max(np.abs(audio_chunk)) if audio_chunk.size else 0.0
                    if peak > 1.0:
                        audio_chunk = audio_chunk / peak

                    all_audio.append(audio_chunk.astype(np.float32))
            finally:
                stop_signal.set()
                audio_streamer.end()
                thread.join(timeout=5)

            if not all_audio:
                raise RuntimeError("No audio generated")

            # Concatenate all chunks
            audio = np.concatenate(all_audio)
            logger.info(f"VibeVoice generated {len(audio)} samples")
            return audio

        except Exception as e:
            logger.error(f"VibeVoice synthesis failed: {e}")
            import traceback

            traceback.print_exc()
            raise

    def synthesize_to_file(self, text: str, output_path: str, **kwargs):
        """Synthesize speech and save to file"""
        audio = self.synthesize(text, **kwargs)
        sf.write(output_path, audio, self.sample_rate)
        logger.info(f"Audio saved to {output_path}")

    def get_available_voices(self) -> List[str]:
        """Get list of available voice names"""
        return list(self.voice_presets.keys())

    def get_default_voice(self) -> str:
        """Get default voice name"""
        return self.default_voice_key or "Carter"

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_path": str(self.model_path),
            "voices": list(self.voice_presets.keys()),
            "default_voice": self.get_default_voice(),
            "sample_rate": self.sample_rate,
            "model_type": "VibeVoice-Realtime",
            "device": self.device,
            "latency": "~300ms first audio",
        }
