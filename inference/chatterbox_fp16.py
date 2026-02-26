#!/usr/bin/env python3
"""
ChatterboxFP16 - Lean TTS using pre-converted FP16 weights

50% less VRAM, 50% smaller on disk vs FP32 original.
Supports 23 languages with voice cloning.

Supported Languages:
    ar (Arabic), da (Danish), de (German), el (Greek), en (English),
    es (Spanish), fi (Finnish), fr (French), he (Hebrew), hi (Hindi),
    it (Italian), ja (Japanese), ko (Korean), ms (Malay), nl (Dutch),
    no (Norwegian), pl (Polish), pt (Portuguese), ru (Russian),
    sv (Swedish), sw (Swahili), tr (Turkish), zh (Chinese)

Usage:
    from chatterbox_fp16 import ChatterboxFP16
    
    model = ChatterboxFP16(device='cuda')
    
    # English (default)
    audio = model.generate("Hello world!")
    
    # French
    audio = model.generate("Bonjour!", language_id='fr')
    
    # Voice cloning
    audio = model.generate("Hello!", audio_prompt="reference.wav")
    
    # Save to file
    import soundfile as sf
    sf.write('output.wav', audio, 24000)
"""

import sys
import os
from pathlib import Path

# Add the chatterbox_fp16 directory to the Python path so it can find the chatterbox module
chatterbox_dir = Path(__file__).parent.parent / "models" / "chatterbox_fp16"
sys.path.insert(0, str(chatterbox_dir))

import torch
import torch.nn.functional as F
import torchaudio
import numpy as np
from safetensors.torch import load_file
from typing import Optional, Union

# Default path to FP16 model files
DEFAULT_MODEL_PATH = Path(__file__).parent.parent / "models" / "chatterbox_fp16"

# Constants
S3_SR = 16000
S3GEN_SR = 24000
ENC_COND_LEN = 6 * S3_SR
DEC_COND_LEN = 10 * S3GEN_SR

# Supported languages
SUPPORTED_LANGUAGES = {
    'ar': 'Arabic', 'da': 'Danish', 'de': 'German', 'el': 'Greek',
    'en': 'English', 'es': 'Spanish', 'fi': 'Finnish', 'fr': 'French',
    'he': 'Hebrew', 'hi': 'Hindi', 'it': 'Italian', 'ja': 'Japanese',
    'ko': 'Korean', 'ms': 'Malay', 'nl': 'Dutch', 'no': 'Norwegian',
    'pl': 'Polish', 'pt': 'Portuguese', 'ru': 'Russian', 'sv': 'Swedish',
    'sw': 'Swahili', 'tr': 'Turkish', 'zh': 'Chinese'
}


class ChatterboxFP16:
    """Chatterbox Multilingual TTS with FP16 precision - 50% less VRAM."""
    
    SAMPLE_RATE = 24000
    
    def __init__(self, model_path=None, device='cuda'):
        """
        Initialize Chatterbox Multilingual TTS with FP16 weights.
        
        Args:
            model_path: Path to directory containing FP16 model files.
                        Defaults to ./chatterbox_multilingual_fp16/
            device: 'cuda' or 'cpu'
        """
        self.device = device
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model path not found: {self.model_path}\n"
                f"Expected files: t3_fp16.safetensors, s3gen_fp16.safetensors, "
                f"ve_fp16.safetensors, conds.pt, tokenizer.json"
            )
        
        self._load_models()
    
    @staticmethod
    def get_supported_languages():
        """Return dict of supported language codes and names."""
        return SUPPORTED_LANGUAGES.copy()
    
    def _load_models(self):
        """Load all model components in FP16."""
        
        from chatterbox.models.t3.t3 import T3
        from chatterbox.models.t3.modules.t3_config import T3Config
        from chatterbox.models.t3.modules.cond_enc import T3Cond
        from chatterbox.models.s3gen.s3gen import S3Token2Wav as S3Gen
        from chatterbox.models.voice_encoder.voice_encoder import VoiceEncoder
        from chatterbox.models.tokenizers.tokenizer import MTLTokenizer
        from chatterbox.models.s3tokenizer import S3Tokenizer
        
        print(f"Loading Multilingual FP16 model from {self.model_path}...")
        
        # T3 Multilingual - vocab size is 2352 (not 2454 as config says)
        print("  Loading T3 (multilingual)...")
        hp = T3Config(text_tokens_dict_size=2352)
        self.t3 = T3(hp).half()
        self.t3.load_state_dict(
            load_file(self.model_path / "t3_fp16.safetensors"), 
            strict=False
        )
        self.t3 = self.t3.to(self.device).eval()
        
        # S3Gen vocoder (same as English)
        print("  Loading S3Gen...")
        self.s3gen = S3Gen().half()
        self.s3gen.load_state_dict(
            load_file(self.model_path / "s3gen_fp16.safetensors"),
            strict=False
        )
        self.s3gen = self.s3gen.to(self.device).eval()
        
        # Voice encoder (same as English)
        print("  Loading VoiceEncoder...")
        self.ve = VoiceEncoder().half()
        self.ve.load_state_dict(
            load_file(self.model_path / "ve_fp16.safetensors"),
            strict=False
        )
        self.ve = self.ve.to(self.device).eval()
        
        # S3 Tokenizer
        print("  Loading S3Tokenizer...")
        self.s3tokenizer = S3Tokenizer()
        self.s3tokenizer = self.s3tokenizer.to(self.device).eval()
        
        # Multilingual text tokenizer
        print("  Loading MTLTokenizer...")
        self.tokenizer = MTLTokenizer(str(self.model_path / "tokenizer.json"))
        
        # Default conditioning
        print("  Loading default conditioning...")
        conds_raw = torch.load(
            self.model_path / "conds.pt",
            map_location='cpu',
            weights_only=False
        )
        
        self._default_t3_cond = T3Cond(
            speaker_emb=conds_raw['t3']['speaker_emb'].half().to(self.device),
            cond_prompt_speech_tokens=conds_raw['t3']['cond_prompt_speech_tokens'].to(self.device),
            emotion_adv=conds_raw['t3']['emotion_adv'].half().to(self.device),
        )
        
        self._default_gen_ref = {}
        for k, v in conds_raw['gen'].items():
            if torch.is_tensor(v):
                if v.is_floating_point():
                    self._default_gen_ref[k] = v.half().to(self.device)
                else:
                    self._default_gen_ref[k] = v.to(self.device)
            else:
                self._default_gen_ref[k] = v
        
        print("  Done!")
    
    def _load_audio(self, audio_path: str) -> torch.Tensor:
        """Load and preprocess audio file."""
        wav, sr = torchaudio.load(audio_path)
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        if sr != S3GEN_SR:
            wav = torchaudio.functional.resample(wav, sr, S3GEN_SR)
        return wav.squeeze(0)
    
    def _prepare_conditioning(self, audio_prompt: str):
        """Extract speaker embedding and reference features from audio prompt."""
        from chatterbox.models.t3.modules.cond_enc import T3Cond
        
        wav = self._load_audio(audio_prompt)
        wav_16k = torchaudio.functional.resample(wav, S3GEN_SR, S3_SR)
        
        speaker_emb = self.ve.embeds_from_wavs(
            [wav_16k.numpy()], 
            sample_rate=S3_SR, 
            as_spk=True
        )
        speaker_emb = torch.from_numpy(speaker_emb).half().to(self.device)
        
        cond_wav = wav_16k[-ENC_COND_LEN:] if len(wav_16k) > ENC_COND_LEN else wav_16k
        cond_wav = cond_wav.unsqueeze(0).to(self.device)
        
        with torch.inference_mode():
            cond_tokens = self.s3tokenizer(cond_wav)
        
        t3_cond = T3Cond(
            speaker_emb=speaker_emb,
            cond_prompt_speech_tokens=cond_tokens,
            emotion_adv=torch.tensor([[[0.5]]], device=self.device, dtype=torch.float16),
        )
        
        ref_wav = wav[-DEC_COND_LEN:] if len(wav) > DEC_COND_LEN else wav
        ref_wav = ref_wav.unsqueeze(0).half().to(self.device)
        
        ref_wav_16k = torchaudio.functional.resample(ref_wav, S3GEN_SR, S3_SR)
        with torch.inference_mode():
            ref_tokens = self.s3tokenizer(ref_wav_16k)
        
        gen_ref = {
            'ref_wav': ref_wav,
            'ref_tokens': ref_tokens,
        }
        
        return t3_cond, gen_ref
    
    def generate(
        self,
        text: str,
        language_id: str = 'en',
        audio_prompt: Optional[str] = None,
        exaggeration: float = 0.3,
        cfg_weight: float = 0.1,
        temperature: float = 0.8,
        repetition_penalty: float = 1.2,
        max_tokens: int = 1000,
    ):
        """
        Generate speech from text in any of 23 supported languages.
        
        Args:
            text: Input text to synthesize
            language_id: Language code (e.g., 'en', 'fr', 'zh', 'ja')
            audio_prompt: Path to reference audio for voice cloning (optional)
            exaggeration: Emotion exaggeration (0-1, higher = more expressive)
            cfg_weight: Classifier-free guidance weight (0-1)
                        Set to 0 for cross-language voice transfer
            temperature: Sampling temperature (higher = more varied)
            repetition_penalty: Penalty for repeated tokens
            max_tokens: Maximum speech tokens to generate
            
        Returns:
            numpy array of audio samples at 24kHz
        """
        from chatterbox.models.t3.modules.cond_enc import T3Cond
        
        # Validate language
        if language_id not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language: {language_id}\n"
                f"Supported: {list(SUPPORTED_LANGUAGES.keys())}"
            )
        
        # Get conditioning
        if audio_prompt:
            t3_cond_base, gen_ref = self._prepare_conditioning(audio_prompt)
        else:
            t3_cond_base = self._default_t3_cond
            gen_ref = self._default_gen_ref
        
        t3_cond = T3Cond(
            speaker_emb=t3_cond_base.speaker_emb,
            cond_prompt_speech_tokens=t3_cond_base.cond_prompt_speech_tokens,
            emotion_adv=torch.tensor([[[exaggeration]]], device=self.device, dtype=torch.float16),
        )
        
        # Tokenize with language-specific processing
        text_tokens = self.tokenizer.text_to_tokens(text, language_id=language_id).to(self.device)
        
        # Duplicate for CFG
        if cfg_weight > 0:
            text_tokens = torch.cat([text_tokens, text_tokens], dim=0)
        
        # Add SOT/EOT
        sot = self.t3.hp.start_text_token
        eot = self.t3.hp.stop_text_token
        text_tokens = F.pad(text_tokens, (1, 0), value=sot)
        text_tokens = F.pad(text_tokens, (0, 1), value=eot)
        
        with torch.inference_mode(), torch.autocast(self.device, dtype=torch.float16):
            speech_tokens = self.t3.inference(
                t3_cond=t3_cond,
                text_tokens=text_tokens,
                max_new_tokens=max_tokens,
                temperature=temperature,
                cfg_weight=cfg_weight,
                repetition_penalty=repetition_penalty,
            )
            
            speech_tokens = speech_tokens[0]
            speech_tokens = speech_tokens[speech_tokens < 6561]
            speech_tokens = speech_tokens.to(self.device)
            
            wav, _ = self.s3gen.inference(
                speech_tokens=speech_tokens,
                ref_dict=gen_ref,
            )
        
        return wav.squeeze(0).cpu().numpy()
    
    def get_vram_usage(self):
        """Return current GPU memory usage in MB."""
        if self.device == 'cuda':
            return torch.cuda.memory_allocated() / 1024 / 1024
        return 0


# =============================================================================
# Test
# =============================================================================
if __name__ == '__main__':
    import time
    import soundfile as sf
    
    print("=" * 60)
    print("ChatterboxFP16 Test")
    print("=" * 60)
    
    print(f"\nSupported languages: {len(SUPPORTED_LANGUAGES)}")
    for code, name in SUPPORTED_LANGUAGES.items():
        print(f"  {code}: {name}")
    
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    
    model = ChatterboxFP16(device='cuda')
    loaded_mem = model.get_vram_usage()
    print(f"\nLoaded VRAM: {loaded_mem:.0f} MB")
    
    # Test English
    print("\n--- English ---")
    start = time.time()
    audio = model.generate("Hello! This is a test of the multilingual model.", language_id='en')
    elapsed = time.time() - start
    duration = len(audio) / 24000
    print(f"Generated {duration:.1f}s audio in {elapsed:.1f}s")
    sf.write('test_en.wav', audio, 24000)
    
    # Test French
    print("\n--- French ---")
    start = time.time()
    audio = model.generate("Bonjour! Ceci est un test du modèle multilingue.", language_id='fr')
    elapsed = time.time() - start
    duration = len(audio) / 24000
    print(f"Generated {duration:.1f}s audio in {elapsed:.1f}s")
    sf.write('test_fr.wav', audio, 24000)
    
    # Test Chinese
    print("\n--- Chinese ---")
    start = time.time()
    audio = model.generate("你好！这是多语言模型的测试。", language_id='zh')
    elapsed = time.time() - start
    duration = len(audio) / 24000
    print(f"Generated {duration:.1f}s audio in {elapsed:.1f}s")
    sf.write('test_zh.wav', audio, 24000)
    
    peak_mem = torch.cuda.max_memory_allocated() / 1024 / 1024
    print(f"\nPeak VRAM: {peak_mem:.0f} MB")
    
    print("\n" + "=" * 60)
    print("SUCCESS!")
    print("=" * 60)
