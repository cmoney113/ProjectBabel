"""
NeuTTS-Nano wrapper for inference directory
"""
import sys
import os
from pathlib import Path

# Add the models/neutts-nano directory to Python path so we can import neutts
neutts_path = Path(__file__).parent.parent / "models" / "neutts-nano"
sys.path.insert(0, str(neutts_path))

try:
    from nano import NeuTTSNano as _NeuTTSNano
    # Re-export the class
    NeuTTSNano = _NeuTTSNano
except ImportError as e:
    print(f"Warning: Could not import NeuTTSNano from {neutts_path}: {e}")
    # Create a fallback class
    class NeuTTSNano:
        def __init__(self, *args, **kwargs):
            raise ImportError("NeuTTSNano is not available. Please ensure the neutts module is properly installed.")