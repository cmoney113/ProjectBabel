#!/usr/bin/env python3
"""
Test script to verify all components of the voice AI assistant
"""

import sys
import os
sys.path.insert(0, '.')

def test_components():
    """Test all major components"""
    print("Testing Voice AI Assistant Components...")
    
    # Test settings manager
    try:
        from src.settings_manager import SettingsManager
        settings = SettingsManager()
        print("✅ Settings Manager: OK")
    except Exception as e:
        print(f"❌ Settings Manager: {e}")
        
    # Test inference module
    try:
        from inference.canary_1b_v2 import Canary1Bv2
        model = Canary1Bv2('./models/canary1b')
        print("✅ Canary ASR Model: OK")
    except Exception as e:
        print(f"❌ Canary ASR Model: {e}")
        
    # Test TTS module
    try:
        from neutts.nano import NeuTTSNano
        tts = NeuTTSNano('./models/neutts-nano')
        print("✅ NeuTTS-Nano: OK")
    except Exception as e:
        print(f"❌ NeuTTS-Nano: {e}")
        
    # Test main window import
    try:
        from src.main import MainWindow
        print("✅ Main Window: OK")
    except Exception as e:
        print(f"❌ Main Window: {e}")
        
    # Test web search
    try:
        from src.web_search import WebSearchManager
        from src.settings_manager import SettingsManager
        settings = SettingsManager()
        web_search = WebSearchManager(settings)
        print("✅ Web Search Manager: OK")
    except Exception as e:
        print(f"❌ Web Search Manager: {e}")
        
    print("\nComponent testing complete!")

if __name__ == "__main__":
    test_components()