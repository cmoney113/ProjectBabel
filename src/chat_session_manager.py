"""
Chat Session Manager
Handles chat history with intelligent session naming
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import hashlib


class ChatSession:
    """Represents a single chat session"""
    
    def __init__(self, session_id: str, name: str, created_at: str = None, messages: List[Dict] = None):
        self.session_id = session_id
        self.name = name
        self.created_at = created_at or datetime.now().isoformat()
        self.messages = messages or []
        self.updated_at = self.created_at
    
    def add_message(self, role: str, content: str):
        """Add a message to the session"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now().isoformat()
    
    def get_preview(self, max_length: int = 50) -> str:
        """Get a preview of the first user message"""
        for msg in self.messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if len(content) > max_length:
                    return content[:max_length] + "..."
                return content
        return "Empty conversation"
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": self.messages
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChatSession":
        session = cls(
            session_id=data["session_id"],
            name=data["name"],
            created_at=data.get("created_at"),
            messages=data.get("messages", [])
        )
        session.updated_at = data.get("updated_at", session.created_at)
        return session


class ChatSessionManager:
    """Manages chat sessions with persistent storage"""
    
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            # Default to project data directory
            storage_dir = Path.home() / ".canary_voice_ai" / "sessions"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.sessions: Dict[str, ChatSession] = {}
        self.current_session_id: Optional[str] = None
        
        self._load_sessions()
    
    def _get_storage_path(self) -> Path:
        """Get the path to the sessions index file"""
        return self.storage_dir / "sessions.json"
    
    def _load_sessions(self):
        """Load all sessions from disk"""
        storage_path = self._get_storage_path()
        
        if storage_path.exists():
            try:
                with open(storage_path, 'r') as f:
                    data = json.load(f)
                    
                for session_data in data.get("sessions", []):
                    session = ChatSession.from_dict(session_data)
                    self.sessions[session.session_id] = session
                
                self.current_session_id = data.get("current_session_id")
                
                # If no current session or current doesn't exist, create new
                if not self.current_session_id or self.current_session_id not in self.sessions:
                    if self.sessions:
                        # Load most recent
                        self.current_session_id = max(
                            self.sessions.keys(),
                            key=lambda k: self.sessions[k].updated_at
                        )
                    else:
                        self.current_session_id = self.create_new_session()
                        
            except Exception as e:
                print(f"Error loading sessions: {e}")
                self.current_session_id = self.create_new_session()
        else:
            self.current_session_id = self.create_new_session()
    
    def _save_sessions(self):
        """Save all sessions to disk"""
        storage_path = self._get_storage_path()
        
        data = {
            "sessions": [s.to_dict() for s in self.sessions.values()],
            "current_session_id": self.current_session_id
        }
        
        with open(storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _generate_session_name(self, first_message: str = None) -> str:
        """Generate an intelligent session name based on first message"""
        if not first_message:
            return f"Chat {datetime.now().strftime('%b %d, %Y %H:%M')}"
        
        # Clean and truncate the message
        clean_message = first_message.strip()
        
        # If it's a short message, use it directly
        if len(clean_message) <= 30:
            return clean_message
        
        # Use first few words + hash for uniqueness
        words = clean_message.split()[:4]
        base_name = " ".join(words)
        
        if len(base_name) > 25:
            base_name = base_name[:25]
        
        # Add a short hash for uniqueness
        hash_suffix = hashlib.md5(clean_message.encode()).hexdigest()[:4]
        
        return f"{base_name}... ({hash_suffix})"
    
    def create_new_session(self, first_message: str = None) -> str:
        """Create a new chat session"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = self._generate_session_name(first_message)
        
        session = ChatSession(session_id=session_id, name=name)
        self.sessions[session_id] = session
        self.current_session_id = session_id
        
        self._save_sessions()
        
        return session_id
    
    def get_current_session(self) -> Optional[ChatSession]:
        """Get the current active session"""
        if self.current_session_id and self.current_session_id in self.sessions:
            return self.sessions[self.current_session_id]
        return None
    
    def switch_session(self, session_id: str) -> bool:
        """Switch to a different session"""
        if session_id in self.sessions:
            self.current_session_id = session_id
            self._save_sessions()
            return True
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            
            # If deleted current session, switch to another
            if self.current_session_id == session_id:
                if self.sessions:
                    self.current_session_id = max(
                        self.sessions.keys(),
                        key=lambda k: self.sessions[k].updated_at
                    )
                else:
                    self.current_session_id = self.create_new_session()
            
            self._save_sessions()
            return True
        return False
    
    def rename_session(self, session_id: str, new_name: str) -> bool:
        """Rename a session"""
        if session_id in self.sessions:
            self.sessions[session_id].name = new_name
            self.sessions[session_id].updated_at = datetime.now().isoformat()
            self._save_sessions()
            return True
        return False
    
    def add_message(self, role: str, content: str):
        """Add a message to the current session"""
        session = self.get_current_session()
        if session:
            session.add_message(role, content)
            self._save_sessions()
    
    def get_all_sessions(self) -> List[ChatSession]:
        """Get all sessions sorted by updated time (newest first)"""
        return sorted(
            self.sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )
    
    def clear_current_session(self):
        """Clear messages in current session but keep the session"""
        session = self.get_current_session()
        if session:
            session.messages = []
            session.updated_at = datetime.now().isoformat()
            self._save_sessions()
