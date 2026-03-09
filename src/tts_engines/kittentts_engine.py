"""
KittenTTS Engine - Using official KittenTTS package
"""

import sys
import warnings
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Suppress phonemizer warnings (words count mismatch is expected)
warnings.filterwarnings("ignore", category=UserWarning, module="phonemizer")

# Add KittenTTS package to path
KITTENTTS_PATH = Path("/home/craig/new-projects/voice_ai/models/kittentts/KittenTTS-main")
if str(KITTENTTS_PATH) not in sys.path:
    sys.path.insert(0, str(KITTENTTS_PATH))


class KittenTTSEngine:
    """KittenTTS engine using official package"""
    
    def __init__(self, model_path: str = None, voices_path: str = None, cache_dir: str = None):
        """Initialize KittenTTS with local model files"""
        
        # Import from local KittenTTS package
        from kittentts.onnx_model import KittenTTS_1_Onnx
        import json
        
        # Default paths
        base_path = Path("/home/craig/new-projects/voice_ai/models/kittentts")
        
        if model_path is None:
            model_path = base_path / "kitten_tts_mini_v0_8.onnx"
        if voices_path is None:
            voices_path = base_path / "voices.npz"
        
        self.model_path = Path(model_path)
        self.voices_path = Path(voices_path)
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        if not self.voices_path.exists():
            raise FileNotFoundError(f"Voices file not found: {self.voices_path}")
        
        # Load config for speed priors and voice aliases
        config_path = base_path / "config.json"
        speed_priors = {}
        voice_aliases = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                speed_priors = config.get("speed_priors", {})
                voice_aliases = config.get("voice_aliases", {})
        
        # Initialize the official KittenTTS ONNX model
        self.model = KittenTTS_1_Onnx(
            model_path=str(self.model_path),
            voices_path=str(self.voices_path),
            speed_priors=speed_priors,
            voice_aliases=voice_aliases
        )
        
        logger.info(f"KittenTTS engine initialized with {len(self.model.available_voices)} voices")
    
    def synthesize(self, text: str, voice: str = "Jasper", speed: float = 1.0, clean_text: bool = True) -> np.ndarray:
        """Synthesize speech from text
        
        Args:
            text: Input text to synthesize
            voice: Voice name (Bella, Jasper, Luna, Bruno, Rosie, Hugo, Kiki, Leo)
            speed: Speech speed (1.0 = normal)
            clean_text: If true, cleanup the text (replace numbers with words)
            
        Returns:
            Audio data as numpy array at 24kHz sample rate
        """
        try:
            logger.info(f"KittenTTS generating audio for: '{text[:50]}...'")
            audio = self.model.generate(text, voice=voice, speed=speed, clean_text=clean_text)
            logger.info(f"KittenTTS generated {len(audio)} samples")
            return audio
        except Exception as e:
            logger.error(f"KittenTTS synthesis failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def synthesize_to_file(self, text: str, output_path: str, voice: str = "Jasper",
                          speed: float = 1.0, clean_text: bool = True) -> None:
        """Synthesize speech and save to file"""
        audio = self.synthesize(text, voice, speed, clean_text)
        sf.write(output_path, audio, 24000)
        logger.info(f"Audio saved to {output_path}")
    
    def get_available_voices(self) -> List[str]:
        """Get list of available voice names"""
        return self.model.all_voice_names.copy()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_path": str(self.model_path),
            "voices_path": str(self.voices_path),
            "available_voices": self.model.all_voice_names,
            "sample_rate": 24000,
            "model_type": "KittenTTS",
            "version": "0.8.0"
        }
