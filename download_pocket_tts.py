#!/usr/bin/env python3
"""Download PocketTTS model from Hugging Face"""

import os
from huggingface_hub import snapshot_download

# Create target directory
target_dir = "/home/craig/new-projects/voice_ai/models/pocketTTS"
os.makedirs(target_dir, exist_ok=True)

# Download the model
print("Downloading PocketTTS model from KevinAHM/pocket-tts-onnx...")
try:
    snapshot_download(
        repo_id="KevinAHM/pocket-tts-onnx",
        local_dir=target_dir,
        local_dir_use_symlinks=False,
        allow_patterns=["onnx/*", "*.json", "*.txt", "README*", "LICENSE*"],
    )
    print(f"✅ Successfully downloaded PocketTTS model to {target_dir}")
except Exception as e:
    print(f"❌ Error downloading model: {e}")
    raise
