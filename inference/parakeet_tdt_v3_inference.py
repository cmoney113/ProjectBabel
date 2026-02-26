#!/usr/bin/env python3
"""
E2E Inference Pipeline & Transcription Service w/ Parakeet TDT 0.6b v3 - 25 Lanaugages, word-lavel timestamps, built-in VAD, and more. We are using an excellent int8 quant of the fp16 model, and the onnx-asr library did an equally excellennt job with exposing all features and handling inferene. So we use his package here.
"""
import onnx_asr
import numpy as np
import sounddevice as sd
import queue
import os
import logging
from datetime import datetime

class LocalParakeetASR:
    def __init__(self):
        # Use files from the models directory
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'models', 'parakeet-tdt-v3')
        
        # Setup logging
        log_dir = os.path.join(model_dir, 'parakeet_transcription.log')
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_dir, mode='a', encoding='utf-8'),
                logging.StreamHandler()  # Also print to console
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        try:
            # Load YOUR models using onnx-asr - using the correct model type for Parakeet TDT v3
            self.model = onnx_asr.load_model(
                model='nemo-parakeet-tdt-0.6b-v3',  # Using Parakeet TDT v3 model
                path=model_dir,
                quantization=None  # Since your models are already int8 quantized
            )
            
            self.logger.info("✅ Loaded YOUR local Parakeet v3 TDT model files with onnx-asr:")
            self.logger.info(f"   - encoder-model.onnx")
            self.logger.info(f"   - decoder_joint-model.onnx") 
            self.logger.info(f"   - vocab.txt")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load model: {e}")
            raise
        
        self.audio_queue = queue.Queue()
    
    def audio_callback(self, indata, frames, time_info, status):
        if status:
            self.logger.debug(f"Audio callback status: {status}")
        audio_data = indata[:, 0].copy()
        self.logger.debug(f"Callback: putting audio chunk, size={len(audio_data)}")
        self.audio_queue.put(audio_data)
    
    def test_model(self):
        """Test that the model can run inference"""
        print("Testing model with dummy audio...")
        
        # Create a short dummy audio signal (more samples to meet feature requirements)
        dummy_audio = np.random.randn(32000).astype(np.float32)  # 2 seconds of audio at 16kHz
        
        try:
            result = self.model.recognize(dummy_audio)
            print(f"✅ Model test completed. Result type: {type(result)}")
            if hasattr(result, 'text'):
                print(f"✅ Text result: {result.text}")
            elif isinstance(result, str):
                print(f"✅ String result: {result}")
            elif isinstance(result, dict):
                print(f"✅ Dict result: {result}")
            else:
                print(f"✅ Raw result: {result}")
            return True
        except Exception as e:
            print(f"❌ Model test failed: {e}")
            return False
    
    def stream(self):
        self.logger.info("🎤 Starting microphone stream...")
        self.logger.info("Press Ctrl+C to stop\n")
        
        # Accumulated audio buffer
        accumulated_audio = np.array([], dtype=np.float32)
        min_audio_length = 16000 * 1.0  # 1.0 second minimum
        max_audio_length = 16000 * 5   # 5 seconds maximum before forced transcription
        silence_threshold = 0.001       # Below this = silence (only need this one parameter. The rest you may see below are over-engineered nonsense implemented by a stupid LLM.
        speech_threshold = 0.002        # Minimum RMS to consider as speech
        silence_frames = 0
        max_silence_frames = 10  # Adjust as needed


        with sd.InputStream(samplerate=16000, channels=1, dtype='float32', 
                          blocksize=1600, callback=self.audio_callback):
            
            chunk_count = 0
            while True:
                try:
                    self.logger.debug("Waiting for audio chunk...")
                    audio_chunk = self.audio_queue.get(timeout=1.0)
                    chunk_count += 1
                    
                    # Calculate RMS for this chunk
                    rms = np.sqrt(np.mean(audio_chunk**2))
                    self.logger.debug(f"Chunk {chunk_count}: RMS={rms:.6f}")
                    
                    # Add chunk to accumulated audio
                    accumulated_audio = np.concatenate([accumulated_audio, audio_chunk])
                    
                    # Track silence
                    if rms < silence_threshold:
                        silence_frames += 1
                    else:
                        silence_frames = 0
                    
                    # Decision: when to transcribe?
                    should_transcribe = False
                    reason = ""
                    
                    # 1. Natural pause detection (silence after speech)
                    if (len(accumulated_audio) >= min_audio_length and 
                        silence_frames >= max_silence_frames):
                        should_transcribe = True
                        reason = "natural pause"
                    
                    # 2. Maximum buffer size reached
                    elif len(accumulated_audio) >= max_audio_length:
                        should_transcribe = True
                        reason = "max buffer"
                    
                    # Check overall buffer RMS
                    buffer_rms = np.sqrt(np.mean(accumulated_audio**2))
                    
                    if should_transcribe and buffer_rms > speech_threshold:
                        self.logger.info(f"Chunk {chunk_count} - Transcribing ({reason}): {len(accumulated_audio)} samples, RMS={buffer_rms:.6f}")
                        
                        try:
                            # Transcribe the accumulated audio
                            result = self.model.recognize(accumulated_audio)
                            
                            # Handle different result types
                            if result:
                                if hasattr(result, 'text'):
                                    text = result.text
                                    # Check for language info
                                    if hasattr(result, 'language'):
                                        lang = result.language
                                    else:
                                        lang = "unknown"
                                elif isinstance(result, dict):
                                    text = result.get('text', '')
                                    lang = result.get('language', 'unknown')
                                elif isinstance(result, str):
                                    text = result
                                    lang = "unknown"
                                else:
                                    text = str(result)
                                    lang = "unknown"
                                
                                # Only log if we have non-empty text
                                if text and text.strip():
                                    if lang != "unknown":
                                        self.logger.info(f"📝 TRANSCRIBED [{lang}]: {text.strip()}")
                                    else:
                                        self.logger.info(f"📝 TRANSCRIBED: {text.strip()}")
                            
                            # Clear the buffer after processing
                            accumulated_audio = np.array([], dtype=np.float32)
                            silence_frames = 0
                            
                        except Exception as e:
                            self.logger.error(f"Transcription failed: {e}")
                            accumulated_audio = np.array([], dtype=np.float32)
                            silence_frames = 0
                    
                    elif should_transcribe and buffer_rms <= speech_threshold:
                        # Silence - discard and reset
                        self.logger.debug(f"Discarding silent buffer (RMS={buffer_rms:.6f})")
                        accumulated_audio = np.array([], dtype=np.float32)
                        silence_frames = 0
                    
                    # Status update
                    if chunk_count % 100 == 0:
                        self.logger.info(f"Chunk {chunk_count} - Buffer: {len(accumulated_audio)} samples, Silence frames: {silence_frames}/{max_silence_frames}")
                        
                except queue.Empty:
                    self.logger.debug("Queue timeout, no audio received")
                    continue

# Use YOUR exact files
if __name__ == "__main__":
    asr = LocalParakeetASR()
    asr.test_model()
    asr.stream()
