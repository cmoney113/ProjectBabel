#!/bin/bash
# Activate virtual environment and run the voice AI assistant

cd "$(dirname "$0")"
export CUDA_VISIBLE_DEVICES=0
. /home/craig/new-projects/voice_ai/venv/bin/activate
python3 src/main.py