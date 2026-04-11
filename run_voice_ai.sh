#!/bin/bash
# Activate virtual environment and run the voice AI assistant

cd "$(dirname "$0")"
export CUDA_VISIBLE_DEVICES=0
export QT_QPA_PLATFORM=wayland
# Suppress Qt warnings (opacity plugin, QML etc)
export QT_LOGGING_RULES="*.warning=false;qml=false"
. /home/craig/new-projects/voice_ai/voiceai-venv/bin/activate
python3 src/main.py
