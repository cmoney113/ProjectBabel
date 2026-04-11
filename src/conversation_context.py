"""
Conversation Context Management System
Modern context management with rolling summaries and conversation memory

Features:
- Rolling conversation window (last N messages)
- Intelligent summarization of conversation history
- Context window optimization for LLM token limits
- Message threading and conversation structure
- Automatic context compression for long conversations
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Individual message in conversation"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str
    message_id: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.message_id is None:
            self.message_id = hashlib.md5(
                f"{self.role}:{self.content}:{self.timestamp}".encode()
            ).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        """Create from dictionary"""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data["timestamp"],
            message_id=data.get("message_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConversationSummary:
    """Summary of conversation context"""
    summary: str
    key_points: List[str]
    timestamp: str
    message_count: int
    conversation_length: int  # approximate token count


class ConversationContextManager:
    """
    Manages conversation context with intelligent summarization and rolling windows
    
    Features:
    - Rolling context window (last N messages)
    - Automatic summarization for long conversations
    - Context compression when approaching token limits
    - Message threading and conversation structure
    """

    def __init__(
        self,
        max_messages: int = 50,
        max_tokens: int = 8000,
        summary_threshold: int = 20,
        rolling_window_size: int = 10,
    ):
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.summary_threshold = summary_threshold
        self.rolling_window_size = rolling_window_size
        
        self.messages: List[ConversationMessage] = []
        self.summaries: List[ConversationSummary] = []
        self.current_context: List[ConversationMessage] = []
        
        # Conversation metadata
        self.conversation_start_time = datetime.now().isoformat()
        self.total_messages = 0
        self.total_tokens = 0

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Add a message to the conversation
        
        Args:
            role: Message role ("user", "assistant", "system")
            content: Message content
            metadata: Optional metadata
            
        Returns:
            message_id: Unique ID for the message
        """
        timestamp = datetime.now().isoformat()
        metadata = metadata or {}
        
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=timestamp,
            metadata=metadata,
        )
        
        self.messages.append(message)
        self.total_messages += 1
        self.total_tokens += self._estimate_tokens(content)
        
        # Update context with rolling window
        self._update_context()
        
        # Check if we need to create a summary
        if len(self.messages) >= self.summary_threshold and len(self.summaries) == 0:
            self._create_summary()
        
        return message.message_id

    def _update_context(self):
        """Update the current context with rolling window and summaries"""
        # Get recent messages (rolling window)
        recent_messages = self.messages[-self.rolling_window_size:]
        
        # If we have summaries, include the most recent one
        context_messages = []
        
        if self.summaries:
            # Add summary as system message
            latest_summary = self.summaries[-1]
            summary_message = ConversationMessage(
                role="system",
                content=f"Previous conversation summary: {latest_summary.summary}\n"
                       f"Key points: {', '.join(latest_summary.key_points[:3])}",
                timestamp=latest_summary.timestamp,
                metadata={"type": "summary"},
            )
            context_messages.append(summary_message)
        
        # Add recent messages
        context_messages.extend(recent_messages)
        
        # Check token limits and compress if needed
        context_tokens = sum(self._estimate_tokens(msg.content) for msg in context_messages)
        
        if context_tokens > self.max_tokens:
            context_messages = self._compress_context(context_messages)
        
        self.current_context = context_messages

    def _compress_context(self, messages: List[ConversationMessage]) -> List[ConversationMessage]:
        """
        Compress context by removing older messages while preserving structure
        """
        if len(messages) <= 2:
            return messages
        
        # Keep system messages and most recent user/assistant pairs
        system_messages = [msg for msg in messages if msg.role == "system"]
        other_messages = [msg for msg in messages if msg.role != "system"]
        
        # Keep the most recent conversation turns
        compressed_messages = system_messages + other_messages[-4:]
        
        logger.info(f"Compressed context from {len(messages)} to {len(compressed_messages)} messages")
        return compressed_messages

    def _create_summary(self):
        """Create a summary of the conversation so far"""
        if len(self.messages) < 5:
            return
        
        # Extract key conversation points
        user_messages = [msg for msg in self.messages if msg.role == "user"]
        assistant_messages = [msg for msg in self.messages if msg.role == "assistant"]
        
        if len(user_messages) < 2:
            return
        
        # Create simple summary based on user queries
        key_points = []
        for msg in user_messages[-5:]:
            content = msg.content[:100]  # Truncate for summary
            if len(content) > 20:
                key_points.append(content)
        
        summary_text = f"Conversation about: {', '.join(key_points[:3])}"
        
        summary = ConversationSummary(
            summary=summary_text,
            key_points=key_points,
            timestamp=datetime.now().isoformat(),
            message_count=len(self.messages),
            conversation_length=self.total_tokens,
        )
        
        self.summaries.append(summary)
        logger.info(f"Created conversation summary: {summary_text}")

    def get_context_for_llm(self) -> List[Dict[str, str]]:
        """
        Get context formatted for LLM API calls
        
        Returns:
            List of message dictionaries with role and content
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.current_context
        ]

    def get_full_conversation(self) -> List[Dict[str, Any]]:
        """Get complete conversation history"""
        return [msg.to_dict() for msg in self.messages]

    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        return {
            "total_messages": self.total_messages,
            "total_tokens": self.total_tokens,
            "current_context_size": len(self.current_context),
            "summaries_count": len(self.summaries),
            "conversation_start": self.conversation_start_time,
        }

    def clear_conversation(self):
        """Clear all conversation data"""
        self.messages.clear()
        self.summaries.clear()
        self.current_context.clear()
        self.total_messages = 0
        self.total_tokens = 0
        self.conversation_start_time = datetime.now().isoformat()

    def save_to_file(self, filepath: str):
        """Save conversation to file"""
        data = {
            "messages": [msg.to_dict() for msg in self.messages],
            "summaries": [
                {
                    "summary": summary.summary,
                    "key_points": summary.key_points,
                    "timestamp": summary.timestamp,
                    "message_count": summary.message_count,
                    "conversation_length": summary.conversation_length,
                }
                for summary in self.summaries
            ],
            "metadata": {
                "conversation_start_time": self.conversation_start_time,
                "total_messages": self.total_messages,
                "total_tokens": self.total_tokens,
            },
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, filepath: str):
        """Load conversation from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.messages = [ConversationMessage.from_dict(msg) for msg in data["messages"]]
            
            self.summaries = [
                ConversationSummary(
                    summary=summary["summary"],
                    key_points=summary["key_points"],
                    timestamp=summary["timestamp"],
                    message_count=summary["message_count"],
                    conversation_length=summary["conversation_length"],
                )
                for summary in data.get("summaries", [])
            ]
            
            metadata = data.get("metadata", {})
            self.conversation_start_time = metadata.get("conversation_start_time", datetime.now().isoformat())
            self.total_messages = metadata.get("total_messages", len(self.messages))
            self.total_tokens = metadata.get("total_tokens", 0)
            
            # Update context
            self._update_context()
            
        except Exception as e:
            logger.error(f"Failed to load conversation from {filepath}: {e}")

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation)
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters for English
        return max(len(text) // 4, 1)


class AdvancedConversationManager:
    """
    Advanced conversation management with topic detection and context optimization
    """

    def __init__(self, base_context_manager: ConversationContextManager):
        self.base_manager = base_context_manager
        self.topics: List[str] = []
        self.current_topic: Optional[str] = None

    def detect_topic_change(self, new_message: str) -> bool:
        """
        Detect if the conversation topic has changed
        
        Args:
            new_message: New user message
            
        Returns:
            True if topic changed, False otherwise
        """
        # Simple topic detection based on keyword changes
        if not self.current_topic:
            self.current_topic = self._extract_topic(new_message)
            return True
        
        new_topic = self._extract_topic(new_message)
        if new_topic != self.current_topic:
            self.topics.append(self.current_topic)
            self.current_topic = new_topic
            return True
        
        return False

    def _extract_topic(self, text: str) -> str:
        """Extract main topic from text"""
        # Simple keyword-based topic extraction
        words = text.lower().split()
        
        # Common topic indicators
        topic_keywords = [
            "python", "code", "programming",
            "ai", "machine learning", "llm",
            "voice", "audio", "speech",
            "help", "question", "explain",
            "search", "find", "information",
        ]
        
        for keyword in topic_keywords:
            if keyword in text.lower():
                return keyword
        
        # Return first few words as topic
        return " ".join(words[:3]) if words else "general"

    def get_enhanced_context(self) -> List[Dict[str, str]]:
        """Get enhanced context with topic information"""
        base_context = self.base_manager.get_context_for_llm()
        
        if self.current_topic:
            # Add topic context as system message
            topic_message = {
                "role": "system",
                "content": f"Current conversation topic: {self.current_topic}",
            }
            base_context.insert(0, topic_message)
        
        return base_context