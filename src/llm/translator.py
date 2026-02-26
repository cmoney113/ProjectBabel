"""
Translation Service using Groq API
=================================
Fast, cheap translation for voice AI pipeline.

Usage:
    from src.llm import translate_text
    result = await translate_text("Hello world", "en", "es")
"""

import os
import logging
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)

# Language code mapping for clarity
LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ru": "Russian", "zh": "Chinese",
    "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
    "tr": "Turkish", "pl": "Polish", "nl": "Dutch", "sv": "Swedish",
    "da": "Danish", "no": "Norwegian", "fi": "Finnish", "el": "Greek",
    "he": "Hebrew", "th": "Thai", "vi": "Vietnamese", "id": "Indonesian"
}

TRANSLATION_PROMPT = """You are a professional translation engine. Translate the following text accurately and naturally.

Rules:
- Preserve the original meaning, tone, and intent
- Keep proper nouns, names, and technical terms in original language if no standard translation exists
- Output ONLY the translation, no explanations, no notes, no quotes

Source language: {source_lang}
Target language: {target_lang}

Text to translate:
{text}

Translation:"""


class TranslationService:
    """Groq-based translation service"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"  # Fast, multilingual
        
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> str:
        """Translate text from source to target language"""
        
        if source_lang == target_lang:
            return text  # No translation needed
            
        source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
        target_name = LANGUAGE_NAMES.get(target_lang, target_lang)
        
        prompt = TRANSLATION_PROMPT.format(
            source_lang=source_name,
            target_lang=target_name,
            text=text
        )
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,  # Low for consistent translation
            "max_tokens": 2000,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url, 
                    json=payload, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"].strip()
                    else:
                        error = await resp.text()
                        logger.error(f"Translation error: {error}")
                        return f"[Translation failed: {resp.status}]"
        except Exception as e:
            logger.error(f"Translation exception: {e}")
            return f"[Translation error: {str(e)}]"
    
    def translate_sync(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> str:
        """Synchronous translation wrapper"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.translate(text, source_lang, target_lang))


# Singleton instance
_translator: Optional[TranslationService] = None

def get_translator() -> TranslationService:
    """Get singleton translator instance"""
    global _translator
    if _translator is None:
        _translator = TranslationService()
    return _translator


async def translate_text(
    text: str, 
    source_lang: str, 
    target_lang: str
) -> str:
    """Quick translation function"""
    translator = get_translator()
    return await translator.translate(text, source_lang, target_lang)
