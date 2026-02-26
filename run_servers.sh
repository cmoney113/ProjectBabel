#!/bin/bash
# Run ASR and TTS FastAPI servers in background
# ASR server: port 8710
# TTS server: port 8711

cd "$(dirname "$0")"
export CUDA_VISIBLE_DEVICES=0
. /home/craig/new-projects/voice_ai/venv/bin/activate

# Run ASR server in background
echo "Starting ASR server on port 8710..."
python -m uvicorn servers.asr_server:app --host 0.0.0.0 --port 8710 &
ASR_PID=$!

# Wait a bit for ASR server to start
sleep 2

# Run TTS server in background
echo "Starting TTS server on port 8711..."
python -m uvicorn servers.tts_server:app --host 0.0.0.0 --port 8711 &
TTS_PID=$!

echo "Servers started!"
echo "ASR server PID: $ASR_PID"
echo "TTS server PID: $TTS_PID"
echo ""
echo "To stop servers, run: kill $ASR_PID $TTS_PID"

# Keep script running
wait
