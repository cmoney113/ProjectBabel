"""
LLM Manager for Canary Voice AI Assistant
Handles interaction with Groq API and response generation
"""

import requests
import json
from typing import List, Dict, Any, Optional
import time


class LLMManager:
    """Manages LLM interactions with Groq API"""
    
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.groq_config = self.settings_manager.get_groq_config()
        self.voice_ai_prompt = self.settings_manager.get_voice_ai_prompt()
        self.post_process_prompt = self.settings_manager.get_post_process_prompt()
        
    def generate_response_with_context(
        self, 
        user_input: str, 
        conversation_history: List[Dict[str, str]], 
        search_results: Optional[str] = None
    ) -> str:
        """Generate AI response with conversation context and optional search results"""
        try:
            # Build messages array
            messages = []
            
            # System prompt
            system_prompt = self.voice_ai_prompt
            if search_results:
                system_prompt += f"\n\nAdditional context from web search:\n{search_results}"
                
            messages.append({"role": "system", "content": system_prompt})
            
            # Conversation history
            messages.extend(conversation_history)
            
            # Current user input
            messages.append({"role": "user", "content": user_input})
            
            # Make API call
            response = self._make_groq_api_call(messages)
            return response
            
        except Exception as e:
            print(f"LLM error: {e}")
            return "I apologize, but I encountered an error processing your request."
            
    def process_dictation(self, transcription: str) -> str:
        """Process dictation with post-processing prompt"""
        try:
            messages = [
                {"role": "system", "content": self.post_process_prompt},
                {"role": "user", "content": transcription}
            ]
            
            response = self._make_groq_api_call(messages)
            return response
            
        except Exception as e:
            print(f"Dictation processing error: {e}")
            return transcription  # Return original if processing fails
            
    def _make_groq_api_call(self, messages: List[Dict[str, str]]) -> str:
        """Make API call to Groq"""
        headers = {
            "Authorization": f"Bearer {self.groq_config['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.groq_config["model"],
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        response = requests.post(
            self.groq_config["endpoint"],
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Groq API error: {response.status_code} - {response.text}")
            
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
        
    def get_confidence_score(self, response: str) -> float:
        """Estimate confidence score for response (simplified implementation)"""
        # In a real implementation, this would use more sophisticated methods
        # For now, we'll use a simple heuristic based on response characteristics
        
        if len(response) < 10:
            return 0.5  # Short responses are less confident
            
        if any(phrase in response.lower() for phrase in [
            "i don't know", "i'm not sure", "maybe", "possibly", 
            "could be", "might be", "uncertain", "unsure"
        ]):
            return 0.6  # Hesitant language indicates lower confidence
            
        return 0.9  # Default high confidence