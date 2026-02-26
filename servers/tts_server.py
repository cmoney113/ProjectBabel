"""
FastAPI server for TTS (Text-to-Speech)
Port: 8711
"""

import sys
import os
import base64
import io
import numpy as np
import torch
from pathlib import Path
from contextlib import asynccontextmanager

# Add project paths first
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "inference"))
qwen_tts_path = Path(__file__).parent.parent / "models" / "qwen_tts_customvoice"
if str(qwen_tts_path) not in sys.path:
    sys.path.insert(0, str(qwen_tts_path))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import soundfile as sf
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model state (lazy loaded)
tts_model = None
current_model_name = None

# Available TTS models
AVAILABLE_TTS_MODELS = {
    "chatterbox-fp16": "Chatterbox FP16 (Multilingual)",
    "sopranotts": "SopranoTTS",
}


def load_tts_model(model_name: str):
    """Load the specified TTS model (lazy loading)"""
    global tts_model, current_model_name

    if current_model_name == model_name and tts_model is not None:
        logger.info(f"TTS model '{model_name}' already loaded")
        return True

    logger.info(f"Loading TTS model: {model_name}")

    if tts_model is not None:
        logger.info(f"Unloading previous TTS model: {current_model_name}")
        tts_model = None
        current_model_name = None

    try:
        if model_name == "chatterbox-fp16":
            sys.path.insert(0, str(Path(__file__).parent.parent / "inference"))
            from chatterbox_fp16 import ChatterboxFP16

            model_dir = Path(__file__).parent.parent / "models" / "chatterbox_fp16"
            device = "cuda" if _check_cuda() else "cpu"
            tts_model = ChatterboxFP16(str(model_dir), device=device)
            current_model_name = model_name
            logger.info("Chatterbox FP16 model loaded successfully")
            return True

        elif model_name == "sopranotts":
            from soprano import SopranoTTS

            model_dir = Path(__file__).parent.parent / "models" / "sopranotts"
            device = "cuda" if _check_cuda() else "cpu"
            tts_model = SopranoTTS(model_path=str(model_dir), device=device)
            current_model_name = model_name
            logger.info("SopranoTTS model loaded successfully")
            return True

        elif model_name == "qwen-tts":
            # Add inference dir to path for local wrapper
            sys.path.insert(0, str(Path(__file__).parent.parent / "inference"))
            from qwen_tts_local import QwenTTSLocal

            model_dir = Path(__file__).parent.parent / "models" / "qwen_tts_customvoice"
            device = "cuda" if _check_cuda() else "cpu"
            tts_model = QwenTTSLocal(
                model_path=str(model_dir), device=device, dtype=torch.bfloat16
            )
            current_model_name = model_name
            logger.info("Qwen-TTS model loaded successfully")
            return True

        else:
            raise ValueError(f"Unknown TTS model: {model_name}")

    except Exception as e:
        logger.error(f"Error loading TTS model {model_name}: {e}")
        tts_model = None
        current_model_name = None
        raise


def _check_cuda():
    """Check if CUDA is available"""
    try:
        import torch

        return torch.cuda.is_available()
    except:
        return False


def generate_speech_tts(text: str, model_name: str, **kwargs):
    """Generate speech using the current TTS model"""
    global tts_model

    if model_name == "neutts-nano":
        voice_id = kwargs.get("voice_id", "default")
        speed = kwargs.get("speed", 1.0)
        pitch = kwargs.get("pitch", 1.0)
        audio = tts_model.generate(text, voice_id=voice_id, speed=speed, pitch=pitch)
        return audio, 24000

    elif model_name == "chatterbox-fp16":
        # Use language_id, not language
        language_id = kwargs.get("language_id", "en")
        exaggeration = kwargs.get("exaggeration", 0.3)
        cfg_weight = kwargs.get("cfg_weight", 0.1)
        temperature = kwargs.get("temperature", 0.8)

        audio = tts_model.generate(
            text,
            language_id=language_id,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            temperature=temperature,
        )
        return audio, 24000

    elif model_name == "sopranotts":
        temperature = kwargs.get("temperature", 0.3)
        top_p = kwargs.get("top_p", 0.95)
        repetition_penalty = kwargs.get("repetition_penalty", 1.2)

        audio = tts_model.infer(
            text,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
        )
        return audio, 32000

    elif model_name == "qwen-tts":
        speaker = kwargs.get("speaker", "Vivian")
        language = kwargs.get("language", "Chinese")
        instruction = kwargs.get("instruction", None)
        non_streaming_mode = kwargs.get("non_streaming_mode", True)

        waveform, sr = tts_model.generate(
            text=text,
            speaker=speaker,
            language=language,
            instruction=instruction,
            non_streaming_mode=non_streaming_mode,
        )
        return waveform, sr

    else:
        raise ValueError(f"Unknown model: {model_name}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    logger.info("TTS FastAPI server starting up...")
    yield
    logger.info("TTS FastAPI server shutting down...")


app = FastAPI(
    title="TTS Server",
    description="Lazy-loading TTS server for voice AI",
    version="1.0.0",
    lifespan=lifespan,
)


class SynthesizeRequest(BaseModel):
    """Request model for speech synthesis"""

    text: str
    model: str = "sopranotts"
    # NeuTTS params
    voice_id: str = "default"
    speed: float = 1.0
    pitch: float = 1.0
    # Chatterbox params
    language: str = "en"
    exaggeration: float = 0.3
    cfg_weight: float = 0.1
    temperature: float = 0.8
    # SopranoTTS params
    top_p: float = 0.95
    repetition_penalty: float = 1.2
    # Qwen-TTS params
    speaker: str = "Vivian"
    instruction: str | None = None
    non_streaming_mode: bool = True


class SynthesizeResponse(BaseModel):
    """Response model for speech synthesis"""

    audio_base64: str
    sample_rate: int
    model: str
    success: bool
    error: str | None = None


@app.get("/")
async def root():
    return {"status": "ok", "service": "tts-server", "port": 8711}


@app.get("/models")
async def list_models():
    """List available TTS models"""
    return {"models": AVAILABLE_TTS_MODELS}


@app.get("/status")
async def status():
    """Get current TTS model status"""
    global current_model_name
    return {
        "loaded_model": current_model_name,
        "is_loaded": tts_model is not None,
        "cuda_available": _check_cuda(),
    }


@app.post("/load")
async def load_model(model: str = "sopranotts"):
    """Load a TTS model"""
    try:
        load_tts_model(model)
        return {"success": True, "model": model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/unload")
async def unload_model():
    """Unload current TTS model"""
    global tts_model, current_model_name
    tts_model = None
    current_model_name = None
    return {"success": True}


@app.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize(request: SynthesizeRequest):
    """Synthesize speech from text"""
    try:
        # Lazy load model if not loaded
        if tts_model is None or current_model_name != request.model:
            load_tts_model(request.model)

        # Build kwargs based on model - convert 'language' to 'language_id' for chatterbox
        kwargs = {}
        if request.model == "neutts-nano":
            kwargs = {
                "voice_id": request.voice_id,
                "speed": request.speed,
                "pitch": request.pitch,
            }
        elif request.model == "chatterbox-fp16":
            kwargs = {
                "language_id": request.language,  # Convert to language_id
                "exaggeration": request.exaggeration,
                "cfg_weight": request.cfg_weight,
                "temperature": request.temperature,
            }
        elif request.model == "sopranotts":
            kwargs = {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "repetition_penalty": request.repetition_penalty,
            }
        elif request.model == "qwen-tts":
            kwargs = {
                "speaker": request.speaker,
                "language": request.language,
                "instruction": request.instruction,
                "non_streaming_mode": request.non_streaming_mode,
            }

        # Generate speech
        audio, sample_rate = generate_speech_tts(request.text, request.model, **kwargs)

        # Convert to base64
        buffer = io.BytesIO()
        sf.write(buffer, audio, sample_rate, format="WAV")
        buffer.seek(0)
        audio_base64 = base64.b64encode(buffer.read()).decode("utf-8")

        return SynthesizeResponse(
            audio_base64=audio_base64,
            sample_rate=sample_rate,
            model=current_model_name,
            success=True,
        )

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        return SynthesizeResponse(
            audio_base64="",
            sample_rate=0,
            model=request.model,
            success=False,
            error=str(e),
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8711)
