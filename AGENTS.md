# Voice AI Assistant - Agent Documentation

## Project Overview

This is a revolutionary Voice AI Assistant application that breaks Wayland's automation barriers. Built with PySide6, featuring real-time speech transcription, conversational AI, voice cloning, and GTT window automation integration using grus for lightning-fast input injection.

### Breakthrough Features
- **Wayland Compatibility**: Uses RemoteDesktop portal instead of uinput for secure, compliant automation
- **Voice Cloning Recording**: Built-in recording with language selection and phonologically dense reference phrases
- **Multi-Language Support**: 11 languages with optimized reference texts for prosody capture
- **grus Integration**: Lightning-fast input injection using RD portal system
- **Dynamic Model Registry**: Single source of truth for all model metadata
- **Real-time Performance**: ~300ms TTS streaming with VibeVoice

### Tech Stack
- **Frontend**: PySide6
- **Backend**: FastAPI servers (TTS/ASR/LLM)
- **Models**: VibeVoice, KaniTTS, Chatterbox FP16, Qwen-TTS, SopranoTTS, KittensTTS
- **API Integrations**: Tavily (search), archive.is (URL extraction), Groq (LLM)
- **Automation**: GTT (GreaterTouchTool) with grus command-line interface

## Changelog

A comprehensive changelog is available via the **Persistent Context & Memory MCP Server**. 

### Accessing Changelog

Agents can retrieve changelog and project history using:

```python
# Query the persistent memory for project changes
from persistent_context import retrieve_context

# Get recent changes and decisions
results = retrieve_context(
    query="voice ai assistant changes",
    sources="ltm,examples"  # long-term memory + example queries
)
```

### Session History

To see session-by-session changes:
```python
# List all sessions for this project
workspace_history(directory="/home/craig/new-projects/voice_ai")
```

## Key Files

### Core Architecture
- `src/model_registry.py` - Dynamic model discovery (single source of truth)
- `src/tts_manager.py` - TTS orchestration with grus integration
- `src/asr_manager.py` - ASR orchestration
- `src/llm_manager.py` - LLM integration
- `src/url_processor.py` - URL → TTS pipeline
- `src/search_processor.py` - Search → TTS pipeline

### UI Components
- `src/ui/pages/voice_ai_page.py` - Main GUI
- `src/ui/pages/voice_cloning/` - Voice cloning UI with recording
- `src/ui/pages/gtt_page.py` - GTT automation tab
- `src/ui/pages/settings_page.py` - Settings management

### Model Inference
- `servers/tts_server.py` - TTS HTTP server with model loading
- `servers/asr_server.py` - ASR HTTP server
- `servers/llm_server.py` - LLM HTTP server
- `inference/kanitts_inference.py` - Enhanced KaniTTS with speaker embedding
- `inference/vibevoice/` - VibeVoice inference
- `inference/chatterbox_fp16/` - Chatterbox FP16 inference

### Model Information

#### TTS Models (from servers/tts_server.py)
- **vibevoice** - Streaming TTS (~300ms) with voice presets (.pt files), 11 languages
- **kanitts** - English-only TTS with speaker embedding from reference audio
- **chatterbox-fp16** - Voice cloning with reference audio (WAV/MP3)
- **qwen-tts** - Qwen TTS multi-language
- **sopranotts** - Soprano TTS multi-language  
- **kittentts** - Kitten TTS multi-language

#### ASR Models (from servers/asr_server.py)
- **canary-1b-v2** - Canary ASR multi-language, high accuracy
- **parakeet-tdt-v3** - Parakeet ASR fast transcription
- **sensevoice-small** - SenseVoice ASR lightweight, fast

## Development Notes

- **Model Loading**: Models are loaded dynamically from server files on first use
- **Voice Cloning**: Supports VibeVoice (.pt presets), Chatterbox FP16 (reference audio), and KaniTTS (speaker embedding)
- **grus Integration**: Replaced wbind with grus for better Wayland compatibility and performance
- **Reference Phrases**: Phonologically dense phrases for each language to capture prosody accurately
- **Recording System**: 30-second max recording with animated progress bar and timer
- **Enterprise Ready**: Production-ready architecture with proper error handling and modular design

## Enterprise Features

- **Wayland Security Compliant**: Uses legitimate RD portals, no security circumvention
- **Single Source of Truth**: ModelRegistry for all model metadata across all UI components
- **Modular Architecture**: Scalable server-based design for enterprise deployment
- **Voice Cloning**: Multi-language support with reference recording and speaker embedding
- **Real-time Performance**: Optimized for low-latency response times
- **Professional UI**: Modern PySide6 interface with proper styling and tooltips

## Built for Enterprise

This project was developed for a $5M enterprise contract and represents breakthrough technology in Linux desktop automation on Wayland.