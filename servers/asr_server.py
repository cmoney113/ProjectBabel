"""
FastAPI server for ASR (Automatic Speech Recognition)
Port: 8710
"""

import sys
import base64
import io
import numpy as np
from pathlib import Path
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import soundfile as sf
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model state (lazy loaded)
asr_model = None
current_model_name = None

# Available ASR models
AVAILABLE_ASR_MODELS = {
    "canary-1b-v2": "Canary 1B v2",
    "parakeet-tdt-v3": "Parakeet TDT v3",
    "sensevoice-small": "SenseVoice Small",
}


def load_asr_model(model_name: str):
    """Load the specified ASR model (lazy loading)"""
    global asr_model, current_model_name

    if current_model_name == model_name and asr_model is not None:
        logger.info(f"ASR model '{model_name}' already loaded")
        return True

    logger.info(f"Loading ASR model: {model_name}")

    # Unload previous model
    if asr_model is not None:
        logger.info(f"Unloading previous ASR model: {current_model_name}")
        asr_model = None
        current_model_name = None

    try:
        if model_name == "canary-1b-v2":
            model_dir = Path(__file__).parent.parent / "models" / "canary1b"
            if not model_dir.exists():
                raise ValueError(f"Canary model directory not found at {model_dir}")

            # Import and load model
            from inference.canary_1b_v2 import Canary1Bv2

            asr_model = Canary1Bv2(model_dir, provider="CPUExecutionProvider")
            current_model_name = model_name
            logger.info("Canary 1B v2 ASR model loaded successfully")
            return True

        elif model_name == "parakeet-tdt-v3":
            model_dir = Path(__file__).parent.parent / "models" / "parakeet-tdt-v3"
            required_files = [
                "encoder-model.onnx",
                "decoder_joint-model.onnx",
                "vocab.txt",
            ]
            missing_files = [f for f in required_files if not (model_dir / f).exists()]

            if missing_files:
                raise ValueError(f"Parakeet model files missing: {missing_files}")

            from inference.parakeet_tdt_v3_inference import LocalParakeetASR

            asr_model = LocalParakeetASR()
            current_model_name = model_name
            logger.info("Parakeet TDT v3 ASR model loaded successfully")
            return True

        elif model_name == "sensevoice-small":
            model_dir = Path(__file__).parent.parent / "models" / "sensevoicesmall"
            if not model_dir.exists():
                raise ValueError(
                    f"SenseVoiceSmall model directory not found at {model_dir}"
                )

            # Import and load SenseVoiceSmall model
            from models.sensevoicesmall.sensevoice_lean import SenseVoiceCTC

            asr_model = SenseVoiceCTC(model_dir, provider="cuda")
            current_model_name = model_name
            logger.info("SenseVoice Small ASR model loaded successfully")
            return True

        else:
            raise ValueError(f"Unknown ASR model: {model_name}")

    except Exception as e:
        logger.error(f"Error loading ASR model {model_name}: {e}")
        asr_model = None
        current_model_name = None
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    logger.info("ASR FastAPI server starting up...")
    yield
    logger.info("ASR FastAPI server shutting down...")


app = FastAPI(
    title="ASR Server",
    description="Lazy-loading ASR server for voice AI",
    version="1.0.0",
    lifespan=lifespan,
)


class TranscribeRequest(BaseModel):
    """Request model for transcription"""

    audio_data: str  # Base64 encoded audio
    model: str = "canary-1b-v2"
    sample_rate: int = 16000
    language: str = "auto"  # Source language (or "auto" for auto-detect)
    target_language: str | None = None  # Target language for translation


class TranscribeResponse(BaseModel):
    """Response model for transcription"""

    text: str
    detected_language: str = "auto"  # Language detected from audio
    model: str
    success: bool
    error: str | None = None


@app.get("/")
async def root():
    return {"status": "ok", "service": "asr-server", "port": 8710}


@app.get("/models")
async def list_models():
    """List available ASR models"""
    return {"models": AVAILABLE_ASR_MODELS}


@app.get("/status")
async def status():
    """Get current ASR model status"""
    global current_model_name
    return {"loaded_model": current_model_name, "is_loaded": asr_model is not None}


@app.post("/load")
async def load_model(model: str = "canary-1b-v2"):
    """Load an ASR model"""
    try:
        load_asr_model(model)
        return {"success": True, "model": model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/unload")
async def unload_model():
    """Unload current ASR model"""
    global asr_model, current_model_name
    asr_model = None
    current_model_name = None
    return {"success": True}


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(request: TranscribeRequest):
    """Transcribe audio data"""
    try:
        # Lazy load model if not loaded
        if asr_model is None or current_model_name != request.model:
            load_asr_model(request.model)

        # Decode base64 audio
        audio_bytes = base64.b64decode(request.audio_data)

        # Convert to numpy array
        audio_buffer = io.BytesIO(audio_bytes)
        audio_array, sr = sf.read(audio_buffer, dtype="float32")

        # Ensure mono
        if len(audio_array.shape) > 1:
            audio_array = audio_array.mean(axis=1)

        # Resample if needed
        if sr != 16000:
            import librosa

            audio_array = librosa.resample(audio_array, orig_sr=sr, target_sr=16000)

        # Transcribe / translate
        detected_lang = request.language
        if request.model == "canary-1b-v2":
            # Pass target_language for translation
            text = asr_model.transcribe(
                audio_array,
                language=request.language,
                target_language=request.target_language,
            )
            # If target_language is set, the output will be translated
            # The source language is detected automatically
            if request.target_language:
                detected_lang = "auto"  # Will be detected by model
        elif request.model == "parakeet-tdt-v3":
            # Parakeet doesn't support translation
            result = asr_model.model.recognize(audio_array)
            if hasattr(result, "text"):
                text = result.text
            elif isinstance(result, dict):
                text = result.get("text", "")
            else:
                text = str(result)
        elif request.model == "sensevoice-small":
            # SenseVoiceSmall supports multiple languages but no translation
            # Use auto-detection or specified language
            lang_map = {
                "en": "en",
                "es": "en",  # Map Spanish to English (not supported)
                "zh": "zh",
                "ja": "ja",
                "ko": "ko",
                "yue": "yue",
                "auto": "auto",
            }
            detected_lang = request.language
            sensevoice_lang = lang_map.get(request.language, "auto")

            # SenseVoiceSmall doesn't support translation, so ignore target_language
            text = asr_model.transcribe(
                audio_array, sample_rate=16000, language=sensevoice_lang, use_itn=True
            )
        else:
            text = ""

        return TranscribeResponse(
            text=text.strip(),
            detected_language=detected_lang,
            model=current_model_name,
            success=True,
        )

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return TranscribeResponse(
            text="", model=request.model, success=False, error=str(e)
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8710)
