# Voice AI Assistant

A modern, enterprise-grade voice AI assistant built with PySide6. Features real-time speech transcription, conversational AI, voice cloning, and GTT window automation integration.

## Features

### Core Voice AI
- **ASR → LLM → TTS Pipeline**: Canary-1b-v2 ASR → Groq LLM → VibeVoice/Chatterbox FP16/SopranoTTS
- **Two modes**:
  - **Voice AI Assistant**: Conversational AI with context awareness
  - **Dictation Mode**: Clean transcription for typing anywhere
- **Trigger options**:
  - **Auto VAD**: Automatic processing when silence is detected
  - **Manual**: Press configurable hotkey (Ctrl+Space by default)

### URL to TTS
- Paste any URL and have it read aloud
- Uses archive.is + readability to extract article content
- Automatically fetches and converts web articles to speech

### Search to TTS
- Search the web using Tavily API
- Select from search results
- Selected article is extracted and read aloud

### Voice Cloning
- **VibeVoice**: Import custom `.pt` voice preset files
- **Chatterbox FP16**: Use reference audio (WAV/MP3) to clone voice
- Manage custom voices in the Voice Cloning tab

### GTT Automation (GreaterTouchTool)
- Window automation integration via GTT CLI
- Automatically type transcribed text anywhere
- Window focus, move, resize operations
- Hotkey scripting and automation

## Requirements

- Python 3.12+
- API Keys (configured in `settings.json`):
  - **Groq API key**: For LLM inference
  - **Tavily API key**: For web search

### Models

The application dynamically discovers models from the server files:
- **TTS Models**: VibeVoice, Chatterbox FP16, SopranoTTS, Qwen-TTS, KittensTTS
- **ASR Models**: Canary-1b-v2, Parakeet TDT, SenseVoice Small

Model files should be placed in:
- `models/` directory (for TTS models)
- Check individual model requirements for file structure

## Installation

1. **Create virtual environment**:
   ```bash
   python3.12 -m venv voice-venv
   source voice-venv/bin/activate  # On Windows: voice-venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install "PySide6-Fluent-Widgets[full]" pyside6 requests numpy sounddevice openwakeword tavily-python
   ```

3. **Configure API keys** in `settings.json`:
   ```json
   {
     "groq_api_key": "your-groq-api-key",
     "tavily_api_key": "your-tavily-api-key"
   }
   ```

4. **Run the application**:
   ```bash
   ./run_voice_ai.sh
   ```

## Usage

### Voice AI Mode (Default)
- Toggle **Auto VAD Trigger** for hands-free operation
- Press **Ctrl+Space** to manually start/stop listening
- Speak naturally; AI responds when you pause
- Responses displayed and spoken via TTS

### Dictation Mode
- Toggle **Dictation Mode** on
- Speech is processed and typed where cursor is located
- Uses GTT for automatic text insertion

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

### Voice Cloning

#### VibeVoice Voice Cloning
1. Go to **Voice Cloning** tab
2. Select **VibeVoice** as the TTS model
3. Click **Import Voice File** to add custom `.pt` voice files
4. Select a voice from the dropdown
5. Use in Voice AI or URL to TTS modes

#### Chatterbox FP16 Voice Cloning
1. Go to **Voice Cloning** tab
2. Select **Chatterbox FP16** as the TTS model
3. Click **Browse** to select reference audio (WAV/MP3)
4. Click **Generate Voice** to create cloned voice
5. Use reference audio in Voice AI mode

### GTT Automation
1. Go to **GTT Automation** tab
2. Configure automation commands
3. Enable "Type with GTT" in settings for dictation
4. Dictated text automatically typed in active window

## Configuration

Settings are stored in `settings.json`:
- **Hotkey**: Manual trigger key (default: Ctrl+Space)
- **VAD Sensitivity**: `silence_timeout_ms` (default: 1500ms)
- **TTS Model**: Default TTS engine
- **ASR Model**: Default ASR engine
- **LLM Model**: Default LLM model
- **GTT Enabled**: Enable GTT integration for dictation

## Architecture

```
voice_ai/
├── src/
│   ├── main.py                 # Application entry point
│   ├── tts_manager.py          # TTS orchestration
│   ├── asr_manager.py          # ASR orchestration
│   ├── llm_manager.py          # LLM integration
│   ├── model_registry.py       # Dynamic model discovery
│   ├── url_processor.py       # URL → TTS pipeline
│   ├── search_processor.py    # Search → TTS pipeline
│   ├── tts_engines/            # TTS engine implementations
│   │   ├── vibevoice_engine.py
│   │   └── ...
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
│   ├── vibevoice/
│   ├── chatterbox_fp16/
│   └── ...
└── models/                     # Model files
```

## API Keys

### Groq
Get your API key from: https://console.groq.com/keys

### Tavily
Get your API key from: https://tavily.com/api/

## Troubleshooting

### TTS Server Issues
- Ensure all model files are in place
- Check port 8001 is available
- Review server logs for errors

### ASR Not Detecting Speech
- Check microphone permissions
- Adjust VAD sensitivity in settings
- Verify audio device is selected

### GTT Not Typing
- Ensure GTT is installed and in PATH
- Check GTT daemon is running
- Verify window focus is correct

## License

This project is for enterprise demonstration purposes.
