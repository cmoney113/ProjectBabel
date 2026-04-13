"""
Base TTS Engine Interface
Defines the contract that all TTS engines must implement
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import numpy as np


class TTSEngine(ABC):
    """Abstract base class for TTS engines"""

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Return the sample rate for this engine"""
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Return the model identifier"""
        pass

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs
    ) -> np.ndarray:
        """
        Synthesize speech from text

        Args:
            text: Input text to synthesize
            voice: Optional voice name/preset
            **kwargs: Engine-specific parameters

        Returns:
            Audio data as numpy float32 array
        """
        pass

    @abstractmethod
    def get_available_voices(self) -> List[str]:
        """Return list of available voice names"""
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """Return model information dictionary"""
        return {
            "model_id": self.model_id,
            "sample_rate": self.sample_rate,
            "voices": self.get_available_voices(),
        }

    def is_loaded(self) -> bool:
        """Check if the model is loaded"""
        return True  # Default implementation

    def load(self) -> bool:
        """Load the model (for lazy loading engines)"""
        return True  # Default implementation

    def unload(self) -> bool:
        """Unload the model to free memory"""
        return True  # Default implementation
