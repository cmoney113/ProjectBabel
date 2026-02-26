# Canary Voice AI Assistant

A modern, sleek voice AI assistant built with PySide6 and Fluent UI widgets. Features real-time speech transcription, conversational AI, and dictation capabilities.

## Features

- **Canary-1b-v2 ASR** → **Groq openai/gpt-oss-120b** → **NeuTTS-Nano** pipeline
- **Two modes**: 
  - **Voice AI Assistant**: Conversational AI with context awareness
  - **Dictation Mode**: Clean transcription output for typing anywhere
- **Trigger options**:
  - **Auto VAD**: Automatic processing when silence is detected
  - **Manual**: Press configurable hotkey (Ctrl+Space by default) to activate
- **Web Search Integration**: Uses Tavily API for current events and comprehensive information
- **Context-aware**: Maintains conversation history for coherent responses
- **Modern UI**: Dark navy theme with Fluent UI animations and transitions
- **Real-time Display**: Shows both user speech and AI response

## Requirements

- Python 3.12
- Canary-1b-v2 ASR model (in `models/canary1b/`)
- NeuTTS-Nano TTS model (in `models/neutts-nano/`)
- Groq API key (configured in `settings.json`)
- Tavily API key (configured in `settings.json`)

## Setup

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
   - `groq_api_key`: Your Groq API key
   - `tavily_api_key`: Your Tavily API key (default dev key included)

4. **Run the application**:
   ```bash
   ./run_voice_ai.sh
   ```

## Usage

### Voice AI Mode (Default)
- Toggle **Auto VAD Trigger** for hands-free operation
- Or press **Ctrl+Space** to manually start listening
- Speak naturally, the AI will respond when you pause
- Responses are displayed and spoken via TTS

### Dictation Mode
- Toggle **Dictation Mode** on
- Your speech will be processed with post-processing rules
- Output is automatically typed wherever your cursor is located (via `gtt` command)

### Configuration
- **Hotkey**: Edit the manual hotkey in the settings
- **VAD Sensitivity**: Adjust `silence_timeout_ms` in `settings.json`
- **Profiles**: Use different profiles for email, code, chat, or documentation

## Models

The application expects the following model directories:
- `models/canary1b/` - Contains Canary ASR model files
- `models/neutts-nano/` - Contains NeuTTS-Nano TTS model files

## Web Search Logic

The assistant automatically performs web searches when:
- Query contains current events keywords (today, news, latest, etc.)
- Query asks for comprehensive/detailed information
- Query requires up-to-date information beyond common knowledge
- Model confidence is below 0.85 threshold

## License

This project is for educational and demonstration purposes. Replace mock implementations with actual model inference code for production use.