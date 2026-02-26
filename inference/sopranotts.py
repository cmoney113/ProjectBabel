"""
SopranoTTS wrapper for inference directory
"""

import sys
import os
from pathlib import Path

# CRITICAL: Add the soprano-inference-server/vocos directory to Python path FIRST
# This must be at index 0 to override any installed vocos package
soprano_server_vocos_path = Path(__file__).parent / "soprano-inference-server" / "vocos"
if str(soprano_server_vocos_path) not in sys.path:
    sys.path.insert(0, str(soprano_server_vocos_path))

# Add the soprano-inference-server directory to Python path for other imports
soprano_server_path = Path(__file__).parent / "soprano-inference-server"
if str(soprano_server_path) not in sys.path:
    sys.path.insert(0, str(soprano_server_path))

# Add the models/sopranotts directory to Python path so we can import soprano_infer
sopranotts_path = Path(__file__).parent.parent / "models" / "sopranotts"
if str(sopranotts_path) not in sys.path:
    sys.path.insert(0, str(sopranotts_path))

try:
    from soprano_infer import SopranoTTS as _SopranoTTS

    # Re-export the class
    SopranoTTS = _SopranoTTS
except ImportError as e:
    print(f"Warning: Could not import SopranoTTS from {sopranotts_path}: {e}")

    # Create a fallback class
    class SopranoTTS:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "SopranoTTS is not available. Please ensure the soprano_infer module is properly installed."
            )

        def infer(self, text, **kwargs):
            raise ImportError(
                "SopranoTTS is not available. Please ensure the soprano_infer module is properly installed."
            )

        def infer_stream(self, text, **kwargs):
            raise ImportError(
                "SopranoTTS is not available. Please ensure the soprano_infer module is properly installed."
            )
