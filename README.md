# Voice AI Assistant

A revolutionary, enterprise-grade voice AI assistant that breaks Wayland's automation barriers. Built with PySide6, featuring real-time speech transcription, conversational AI, voice cloning, and GTT window automation integration using grus for lightning-fast input injection.

## 🚀 Breakthrough Features

### Core Voice AI Pipeline
- **ASR → LLM → TTS Pipeline**: Canary-1b-v2 ASR → iFlow SOTA Models via API → VibeVoice/Chatterbox FP16/KaniTTS/SopranoTTS
- **Two modes**:
  - **Voice AI Assistant**: Conversational AI with context awareness
  - **Dictation Mode**: Clean transcription for typing anywhere
- **Trigger options**:
  - **Auto VAD**: Automatic processing when silence is detected
  - **Manual**: Press configurable hotkey (Ctrl+Space by default)

### Voice Cloning Revolution
- **Record Reference Audio**: Built-in recording with language selection and phonologically dense reference phrases
- **Multi-Language Support**: 11 languages with optimized reference texts for prosody capture
- **Model Support**:
  - **VibeVoice**: Import custom `.pt` voice preset files (11 languages)
  - **Chatterbox FP16**: Use reference audio (WAV/MP3) for voice cloning
  - **KaniTTS**: Speaker embedding from reference audio (English)
- **Timer + Progress Bar**: 30-second recording with animated progress

### URL to TTS
- Paste any URL and have it read aloud
- Uses archive.is + readability to extract article content
- Automatically fetches and converts web articles to speech

### Search to TTS
- Search the web using Tavily API
- Select from search results
- Selected article is extracted and read aloud

### GTT Automation (GreaterTouchTool)
- **grus Integration**: Lightning-fast input injection using RD portal system
- **Window automation**: Focus, move, resize operations
- **Hotkey scripting**: Custom automation sequences
- **Dictation typing**: Automatic text insertion anywhere

## 🏗️ Architecture Breakthrough

### Wayland Compatibility
- **grus**: Uses RemoteDesktop portal instead of uinput
- **Lightning performance**: RD input injection system
- **Security compliant**: Works within Wayland's security model
- **Enterprise ready**: No security circumvention required

### Dynamic Model Registry
- **Single source of truth**: All model metadata in one location
- **Auto-discovery**: Models discovered from server files
- **Rich metadata**: Languages, voice cloning support, streaming, descriptions
- **GUI integration**: All dropdowns populate from registry

### Modular Design
- **TTS Engines**: VibeVoice, Chatterbox FP16, KaniTTS, SopranoTTS, Qwen-TTS, KittensTTS
- **ASR Engines**: Canary-1b-v2, Parakeet TDT, SenseVoice Small
- **HTTP Servers**: Separate TTS/ASR/LLM servers for scalability
- **UI Pages**: Dedicated tabs for each major feature

## 📋 Requirements

- Python 3.12+
- Linux with Wayland (X11 also supported)
- GTT (GreaterTouchTool) for automation
- API Keys (configured in `settings.json`):
  - **Groq API key**: For LLM inference
  - **Tavily API key**: For web search

## 🚀 Installation

1. **Create virtual environment**:
   ```bash
   python3.12 -m venv voice-venv
   source voice-venv/bin/activate  # On Windows: voice-venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install "PySide6-Fluent-Widgets[full]" pyside6 requests numpy sounddevice openwakeword tavily-python
   ```

3. **Install GTT** (GreaterTouchTool):
   ```bash
   # Install via your package manager or download from GTT releases
   sudo apt install gtt  # Ubuntu/Debian
   # or
   yay -S gtt  # Arch
   ```

4. **Configure API keys** in `settings.json`:
   ```json
   {
     "groq_api_key": "your-groq-api-key",
     "tavily_api_key": "your-tavily-api-key"
   }
   ```

5. **Run the application**:
   ```bash
   ./run_voice_ai.sh
   ```

## 🎯 Usage Guide

### Voice AI Mode (Default)
- Toggle **Auto VAD Trigger** for hands-free operation
- Press **Ctrl+Space** to manually start/stop listening
- Speak naturally; AI responds when you pause
- Responses displayed and spoken via TTS

### Voice Cloning Recording
1. Go to **Voice Cloning** tab
2. Select your **Language** from dropdown
3. Read the **Reference Text** displayed
4. Click **Record** (30s max with progress bar)
5. Preview and save your recording
6. Select **VibeVoice**, **Chatterbox FP16**, or **KaniTTS**
7. Generate cloned voice and use in Voice AI mode

### Dictation Mode
- Toggle **Dictation Mode** on
- Speech is processed and typed where cursor is located
- Uses **grus** for lightning-fast text insertion
- Works on Wayland and X11

### URL to TTS
1. Go to **URL to TTS** tab
2. Paste any URL (article, news, blog)
3. Click **Fetch & Speak** or press Enter
4. Article is extracted and read aloud

### Search to TTS
1. Go to **Search to TTS** tab
2. Enter your search query
3. Click **Search** or press Enter
4. Browse results, click **Speak** on any result
5. Article is extracted and read aloud

### GTT Automation
1. Go to **GTT Automation** tab
2. Configure automation commands
3. Enable "Type with GTT" in settings for dictation
4. Dictated text automatically typed in active window

## ⚙️ Configuration

Settings are stored in `settings.json`:
- **Hotkey**: Manual trigger key (default: Ctrl+Space)
- **VAD Sensitivity**: `silence_timeout_ms` (default: 1500ms)
- **TTS Model**: Default TTS engine
- **ASR Model**: Default ASR engine
- **LLM Model**: Default LLM model
- **Typing Mode**: grus (default), clipboard, or system
- **Voice Cloning**: Reference audio settings

## 🏛️ Architecture

```
voice_ai/
├── src/
│   ├── main.py                 # Application entry point
│   ├── tts_manager.py          # TTS orchestration with grus integration
│   ├── asr_manager.py          # ASR orchestration
│   ├── llm_manager.py          # LLM integration
│   ├── model_registry.py       # Dynamic model discovery (single source of truth)
│   ├── url_processor.py       # URL → TTS pipeline
│   ├── search_processor.py    # Search → TTS pipeline
│   ├── languages.py           # Language utilities (now uses ModelRegistry)
│   ├── tts_engines/           # TTS engine implementations
│   │   ├── vibevoice_engine.py
│   │   ├── kanitts_engine.py
│   │   └── chatterbox_fp16_engine.py
│   └── ui/
│       ├── main_window.py      # Main application window
│       └── pages/              # Tab pages
│           ├── voice_ai_page.py
│           ├── url_tts_page.py
│           ├── search_tts_page.py
│           ├── voice_cloning_page.py
│           ├── gtt_page.py
│           └── settings_page.py
├── servers/
│   ├── tts_server.py           # TTS HTTP server
│   ├── asr_server.py           # ASR HTTP server
│   └── llm_server.py           # LLM HTTP server
├── inference/                  # Model inference code
│   ├── kanitts_inference.py    # Enhanced with speaker embedding
│   ├── vibevoice/
│   ├── chatterbox_fp16/
│   └── kanitts/
└── models/                     # Model files (excluded from git)
```

## 🔑 API Keys

### Groq
Get your API key from: https://console.groq.com/keys

### Tavily
Get your API key from: https://tavily.com/api/

## 🛠️ Model Support

### TTS Models (Dynamic Discovery)
- **VibeVoice**: Multi-language, ~300ms streaming, voice cloning with .pt files
- **Chatterbox FP16**: English, voice cloning with reference audio
- **KaniTTS**: English, voice cloning with speaker embedding
- **SopranoTTS**: Multi-language
- **Qwen-TTS**: Multi-language
- **KittensTTS**: Multi-language

### ASR Models
- **Canary-1b-v2**: Multi-language, high accuracy
- **Parakeet TDT**: Fast transcription
- **SenseVoice Small**: Lightweight, fast

## 🚨 Troubleshooting

### TTS Server Issues
- Ensure all model files are in place
- Check port 8001 is available
- Review server logs for errors

### ASR Not Detecting Speech
- Check microphone permissions
- Adjust VAD sensitivity in settings
- Verify audio device is selected

### grus Not Typing (Wayland)
- Ensure GTT is installed: `which grus`
- Check GTT daemon is running: `systemctl --user status gtt`
- Verify window focus is correct
- Test manually: `grus --type-text "Hello World"`

### Voice Cloning Recording Issues
- Check microphone permissions
- Ensure 30-second recording limit
- Verify reference audio quality
- Check language selection matches voice

## 🏆 Enterprise Features

- **Wayland Security Compliant**: Uses legitimate RD portals
- **Single Source of Truth**: ModelRegistry for all model metadata
- **Modular Architecture**: Scalable server-based design
- **Voice Cloning**: Multi-language support with reference recording
- **Real-time Performance**: ~300ms TTS streaming
- **Professional UI**: PySide6 with modern styling

## 📄 License

This project is for enterprise demonstration purposes.

---

**Built for the $5M enterprise contract - production ready with Wayland breakthrough technology.**