"""
FastAPI server for Fun-ASR-vLLM (Automatic Speech Recognition)
Port: 8712
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

# Add Fun-ASR-vllm to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Fun-ASR-vllm"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model state (lazy loaded)
asr_model = None
vllm_model = None
current_model_name = None

# Available ASR models
AVAILABLE_ASR_MODELS = {
    "fun-asr-mlt-nano-2512": "Fun-ASR MLT Nano 2512",
}


def load_asr_model(model_name: str):
    """Load the specified ASR model with vLLM acceleration (lazy loading)"""
    global asr_model, vllm_model, current_model_name

    if current_model_name == model_name and asr_model is not None:
        logger.info(f"ASR model '{model_name}' already loaded")
        return True

    logger.info(f"Loading ASR model: {model_name}")

    # Unload previous model
    if asr_model is not None:
        logger.info(f"Unloading previous ASR model: {current_model_name}")
        asr_model = None
        vllm_model = None
        current_model_name = None

    try:
        if model_name == "fun-asr-mlt-nano-2512":
            model_dir = Path(__file__).parent.parent / "models" / "FunASR-MLT-2512"
            if not model_dir.exists():
                raise ValueError(f"Fun-ASR model directory not found at {model_dir}")

            # Import and load model
            from model import FunASRNano
            from vllm import LLM, SamplingParams

            # Load the base model
            asr_model, kwargs = FunASRNano.from_pretrained(
                model=str(model_dir), device="cuda:0"
            )
            asr_model.eval()

            # Initialize vLLM for acceleration
            vllm_model = LLM(
                model="yuekai/Fun-ASR-MLT-Nano-2512-vllm",
                enable_prompt_embeds=True,
                gpu_memory_utilization=0.4,
            )

            # Attach vLLM to the ASR model
            asr_model.vllm = vllm_model
            asr_model.vllm_sampling_params = SamplingParams(top_p=0.001, max_tokens=500)

            current_model_name = model_name
            logger.info(
                "Fun-ASR MLT Nano 2512 ASR model loaded successfully with vLLM acceleration"
            )
            return True
        else:
            raise ValueError(f"Unknown ASR model: {model_name}")

    except Exception as e:
        logger.error(f"Error loading ASR model {model_name}: {e}")
        asr_model = None
        vllm_model = None
        current_model_name = None
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    logger.info("Fun-ASR-vLLM FastAPI server starting up...")
    yield
    logger.info("Fun-ASR-vLLM FastAPI server shutting down...")


app = FastAPI(
    title="Fun-ASR-vLLM Server",
    description="Lazy-loading ASR server with vLLM acceleration for voice AI",
    version="1.0.0",
    lifespan=lifespan,
)


class TranscribeRequest(BaseModel):
    """Request model for transcription"""

    audio_data: str  # Base64 encoded audio
    model: str = "fun-asr-mlt-nano-2512"
    sample_rate: int = 16000
    language: str = "英文"  # Language for Fun-ASR (Chinese: 中文, English: 英文, etc.)


class TranscribeResponse(BaseModel):
    """Response model for transcription"""

    text: str
    detected_language: str = "auto"  # Language detected from audio
    model: str
    success: bool
    error: str | None = None


@app.get("/")
async def root():
    return {"status": "ok", "service": "fun-asr-vllm-server", "port": 8712}


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
async def load_model(model: str = "fun-asr-mlt-nano-2512"):
    """Load an ASR model"""
    try:
        load_asr_model(model)
        return {"success": True, "model": model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/unload")
async def unload_model():
    """Unload current ASR model"""
    global asr_model, vllm_model, current_model_name
    asr_model = None
    vllm_model = None
    current_model_name = None
    return {"success": True}


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(request: TranscribeRequest):
    """Transcribe audio data with vLLM acceleration"""
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

        # Save temporary audio file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            sf.write(tmp_file.name, audio_array, 16000)
            audio_path = tmp_file.name

        # Transcribe with vLLM acceleration
        res = asr_model.inference(
            data_in=[audio_path], language=request.language, **{"device": "cuda:0"}
        )

        # Clean up temporary file
        import os

        os.unlink(audio_path)

        text = res[0][0]["text"]

        return TranscribeResponse(
            text=text.strip(),
            detected_language="auto",
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

    uvicorn.run(app, host="0.0.0.0", port=8712)
