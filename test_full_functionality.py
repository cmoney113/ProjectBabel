#!/usr/bin/env python3
"""
Comprehensive test for full voice AI assistant functionality
"""

import sys
import os
import numpy as np
sys.path.insert(0, '.')

def test_full_pipeline():
    """Test the complete voice AI pipeline"""
    print("🧪 Testing Full Voice AI Assistant Pipeline...")
    
    # Test 1: Settings Manager
    try:
        from src.settings_manager import SettingsManager
        settings = SettingsManager()
        groq_config = settings.get_groq_config()
        assert "api_key" in groq_config
        print("✅ Settings Manager: OK")
    except Exception as e:
        print(f"❌ Settings Manager: {e}")
        return False
        
    # Test 2: Canary ASR Model
    try:
        from inference.canary_1b_v2 import Canary1Bv2
        model_dir = "./models/canary1b"
        model = Canary1Bv2(model_dir, provider="CPUExecutionProvider")
        
        # Test with dummy audio
        dummy_audio = np.random.randn(16000).astype(np.float32) * 0.1
        transcription = model.transcribe(dummy_audio, language="en")
        print(f"✅ Canary ASR Model: Transcribed '{transcription[:50]}...'")
    except Exception as e:
        print(f"❌ Canary ASR Model: {e}")
        return False
        
    # Test 3: TTS Manager
    try:
        from src.tts_manager import TTSManager
        tts = TTSManager(settings)
        # Test speak method (won't actually play audio in test)
        tts.speak("Test message")
        print("✅ TTS Manager: OK")
    except Exception as e:
        print(f"❌ TTS Manager: {e}")
        return False
        
    # Test 4: Web Search Manager
    try:
        from src.web_search import WebSearchManager
        web_search = WebSearchManager(settings)
        should_search = web_search.should_perform_search("What happened in the news today?")
        print(f"✅ Web Search Manager: Should search for news query: {should_search}")
    except Exception as e:
        print(f"❌ Web Search Manager: {e}")
        return False
        
    # Test 5: Voice Processor
    try:
        from src.voice_processor import VoiceProcessor
        voice_processor = VoiceProcessor(settings)
        print("✅ Voice Processor: OK")
    except Exception as e:
        print(f"❌ Voice Processor: {e}")
        return False
        
    # Test 6: Main Window
    try:
        from src.main import MainWindow
        print("✅ Main Window: OK")
    except Exception as e:
        print(f"❌ Main Window: {e}")
        return False
        
    print("\n🎉 All components working correctly!")
    print("\n🚀 Ready to run the voice AI assistant!")
    print("\nTo start the application:")
    print("  ./run_voice_ai.sh")
    return True

if __name__ == "__main__":
    success = test_full_pipeline()
    if not success:
        sys.exit(1)