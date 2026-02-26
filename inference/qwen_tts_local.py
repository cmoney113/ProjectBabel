"""
Qwen-TTS local inference wrapper - loads directly from Qwen3-TTS-main without pip dependency
"""

import sys
from pathlib import Path

# Add Qwen3-TTS-main to path BEFORE importing torch
qwen_main = (
    Path(__file__).parent.parent / "models" / "qwen_tts_customvoice" / "Qwen3-TTS-main"
)
if str(qwen_main) not in sys.path:
    sys.path.insert(0, str(qwen_main))

import torch
import numpy as np
from typing import Optional, Union, Tuple


class QwenTTSLocal:
    """Local Qwen-TTS inference using Qwen3-TTS-main package"""

    SPEAKERS = {
        "Vivian": "Chinese",
        "Serena": "Chinese",
        "Uncle_Fu": "Chinese",
        "Dylan": "Chinese",
        "Eric": "Chinese",
        "Ryan": "English",
        "Aiden": "English",
        "Ono_Anna": "Japanese",
        "Sohee": "Korean",
    }

    LANGUAGES = [
        "Chinese",
        "English",
        "Japanese",
        "Korean",
        "German",
        "French",
        "Russian",
        "Portuguese",
        "Spanish",
        "Italian",
    ]

    def __init__(
        self, model_path: str, device: str = "cuda", dtype: torch.dtype = torch.bfloat16
    ):
        self.model_path = model_path
        self.device = device
        self.dtype = dtype

        # Import from local Qwen3-TTS-main
        from qwen_tts.core.models.modeling_qwen3_tts import (
            Qwen3TTSForConditionalGeneration,
        )
        from transformers import AutoProcessor, AutoConfig

        # Load model
        self.model = Qwen3TTSForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype=dtype,
            device_map=device,
        )

        # Load processor
        self.processor = AutoProcessor.from_pretrained(model_path)

    def generate(
        self,
        text: str,
        speaker: str = "Vivian",
        language: Optional[str] = None,
        instruction: Optional[str] = None,
        non_streaming_mode: bool = True,
    ) -> Tuple[np.ndarray, int]:
        """Generate speech"""
        if speaker not in self.SPEAKERS:
            raise ValueError(
                f"Invalid speaker: {speaker}. Available: {list(self.SPEAKERS.keys())}"
            )

        if language is None:
            language = self.SPEAKERS[speaker]

        if language not in self.LANGUAGES:
            raise ValueError(
                f"Invalid language: {language}. Available: {self.LANGUAGES}"
            )

        # Generate
        inputs = self.processor(
            text=text,
            language=language,
            speaker=speaker,
            instruct_text=instruction,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            output = self.model.generate(
                **inputs, non_streaming_mode=non_streaming_mode
            )

        waveform = output.audio[0].cpu().numpy()
        return waveform, output.sample_rate


def load_qwen_tts(model_path: str, device: str = "cuda", dtype=torch.bfloat16):
    """Convenience function to load Qwen-TTS"""
    return QwenTTSLocal(model_path, device, dtype)
