"""
Projects Manager - Database operations for Perplexity-like Spaces feature
Handles project creation, context storage, and chat sessions with SQLite backend.
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of context that can be added to a project"""
    FILE = "file"
    URL = "url"
    TEXT = "text"
    IMAGE = "image"


@dataclass
class Project:
    """Represents a project space"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    system_prompt: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectContext:
    """Represents a piece of context within a project"""
    id: Optional[int] = None
    project_id: int = 0
    context_type: str = ""  # file, url, text, image
    source: str = ""  # file path, URL, or text preview
    content: str = ""  # extracted text content
    metadata: Dict[str, Any] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "context_type": self.context_type,
            "source": self.source,
            "content": self.content,
            "metadata": json.dumps(self.metadata) if self.metadata else "{}",
            "created_at": self.created_at,
        }


@dataclass
class ProjectChatSession:
    """Represents a chat session within a project"""
    id: Optional[int] = None
    project_id: int = 0
    name: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectChatMessage:
    """Represents a message in a project chat session"""
    id: Optional[int] = None
    session_id: int = 0
    role: str = ""  # user, assistant
    content: str = ""
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProjectsManager:
    """Manages projects, context, and chat sessions in SQLite database"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Store in user's home directory
            data_dir = Path.home() / ".canary_voice_ai" / "projects"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "projects.db"

        self.db_path = str(db_path)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    system_prompt TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Project context table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    context_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            # Project chat sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

            # Project chat messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES project_chat_sessions(id) ON DELETE CASCADE
                )
            """)

            conn.commit()
            logger.info("Projects database initialized")

    # ==================== Project Operations ====================

    def create_project(self, name: str, description: str = "", system_prompt: str = "") -> Project:
        """Create a new project"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO projects (name, description, system_prompt, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (name, description, system_prompt),
            )
            conn.commit()

            project_id = cursor.lastrowid
            return self.get_project(project_id)

    def get_project(self, project_id: int) -> Optional[Project]:
        """Get a project by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()

            if row:
                return Project(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    system_prompt=row["system_prompt"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            return None

    def get_all_projects(self) -> List[Project]:
        """Get all projects sorted by updated_at (newest first)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC"
            )
            rows = cursor.fetchall()

            return [
                Project(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    system_prompt=row["system_prompt"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    def update_project(self, project_id: int, **kwargs) -> bool:
        """Update project fields"""
        allowed_fields = {"name", "description", "system_prompt"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [project_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE projects SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values,
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_project(self, project_id: int) -> bool:
        """Delete a project and all associated data"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== Context Operations ====================

    def add_context(
        self,
        project_id: int,
        context_type: ContextType,
        source: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ) -> ProjectContext:
        """Add context to a project"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            metadata_json = json.dumps(metadata) if metadata else "{}"

            cursor.execute(
                """
                INSERT INTO project_context (project_id, context_type, source, content, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, context_type.value, source, content, metadata_json),
            )
            conn.commit()

            context_id = cursor.lastrowid

            # Update project's updated_at timestamp
            cursor.execute(
                "UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (project_id,),
            )
            conn.commit()

            return self.get_context(context_id)

    def get_context(self, context_id: int) -> Optional[ProjectContext]:
        """Get a context item by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM project_context WHERE id = ?", (context_id,))
            row = cursor.fetchone()

            if row:
                return ProjectContext(
                    id=row["id"],
                    project_id=row["project_id"],
                    context_type=row["context_type"],
                    source=row["source"],
                    content=row["content"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"],
                )
            return None

    def get_project_context(self, project_id: int) -> List[ProjectContext]:
        """Get all context for a project"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM project_context WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            )
            rows = cursor.fetchall()

            return [
                ProjectContext(
                    id=row["id"],
                    project_id=row["project_id"],
                    context_type=row["context_type"],
                    source=row["source"],
                    content=row["content"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def get_context_text_for_llm(self, project_id: int, max_chars: int = 8000) -> str:
        """Get all context formatted for LLM consumption"""
        contexts = self.get_project_context(project_id)

        if not contexts:
            return ""

        formatted_parts = []
        total_chars = 0

        for ctx in contexts:
            prefix = f"[{ctx.context_type.upper()}] {ctx.source}\n"
            content = ctx.content[:2000]  # Limit each context piece
            formatted = prefix + content + "\n\n"

            if total_chars + len(formatted) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    formatted_parts.append(formatted[:remaining])
                break

            formatted_parts.append(formatted)
            total_chars += len(formatted)

        return "".join(formatted_parts)

    def delete_context(self, context_id: int) -> bool:
        """Delete a context item"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM project_context WHERE id = ?", (context_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== Chat Session Operations ====================

    def create_chat_session(self, project_id: int, name: str = None) -> ProjectChatSession:
        """Create a new chat session within a project"""
        if name is None:
            name = f"Chat {datetime.now().strftime('%b %d, %H:%M')}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO project_chat_sessions (project_id, name, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (project_id, name),
            )
            conn.commit()

            session_id = cursor.lastrowid
            return self.get_chat_session(session_id)

    def get_chat_session(self, session_id: int) -> Optional[ProjectChatSession]:
        """Get a chat session by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM project_chat_sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()

            if row:
                return ProjectChatSession(
                    id=row["id"],
                    project_id=row["project_id"],
                    name=row["name"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            return None

    def get_project_chat_sessions(self, project_id: int) -> List[ProjectChatSession]:
        """Get all chat sessions for a project"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM project_chat_sessions WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,),
            )
            rows = cursor.fetchall()

            return [
                ProjectChatSession(
                    id=row["id"],
                    project_id=row["project_id"],
                    name=row["name"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    def update_chat_session(self, session_id: int, name: str) -> bool:
        """Update chat session name"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE project_chat_sessions SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (name, session_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_chat_session(self, session_id: int) -> bool:
        """Delete a chat session and all its messages"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM project_chat_sessions WHERE id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== Chat Message Operations ====================

    def add_chat_message(
        self, session_id: int, role: str, content: str
    ) -> ProjectChatMessage:
        """Add a message to a chat session"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO project_chat_messages (session_id, role, content)
                VALUES (?, ?, ?)
                """,
                (session_id, role, content),
            )

            # Update session's updated_at
            cursor.execute(
                """
                UPDATE project_chat_sessions
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (session_id,),
            )

            conn.commit()

            message_id = cursor.lastrowid
            return self.get_chat_message(message_id)

    def get_chat_message(self, message_id: int) -> Optional[ProjectChatMessage]:
        """Get a chat message by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM project_chat_messages WHERE id = ?", (message_id,)
            )
            row = cursor.fetchone()

            if row:
                return ProjectChatMessage(
                    id=row["id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    timestamp=row["timestamp"],
                )
            return None

    def get_chat_messages(self, session_id: int) -> List[ProjectChatMessage]:
        """Get all messages in a chat session, ordered by timestamp"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM project_chat_messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
                """,
                (session_id,),
            )
            rows = cursor.fetchall()

            return [
                ProjectChatMessage(
                    id=row["id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    timestamp=row["timestamp"],
                )
                for row in rows
            ]

    def get_chat_history_for_llm(self, session_id: int, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get chat history formatted for LLM consumption"""
        messages = self.get_chat_messages(session_id)

        # Take last N messages
        messages = messages[-max_messages:] if len(messages) > max_messages else messages

        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    def clear_chat_session(self, session_id: int) -> bool:
        """Clear all messages from a chat session"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM project_chat_messages WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            return cursor.rowcount >= 0

    # ==================== Utility Methods ====================

    def search_context(self, project_id: int, query: str) -> List[ProjectContext]:
        """Search context content for a query"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM project_context
                WHERE project_id = ? AND content LIKE ?
                ORDER BY created_at DESC
                """,
                (project_id, f"%{query}%"),
            )
            rows = cursor.fetchall()

            return [
                ProjectContext(
                    id=row["id"],
                    project_id=row["project_id"],
                    context_type=row["context_type"],
                    source=row["source"],
                    content=row["content"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def get_stats(self, project_id: int) -> Dict[str, int]:
        """Get statistics for a project"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Count context items
            cursor.execute(
                "SELECT COUNT(*) FROM project_context WHERE project_id = ?",
                (project_id,),
            )
            context_count = cursor.fetchone()[0]

            # Count chat sessions
            cursor.execute(
                "SELECT COUNT(*) FROM project_chat_sessions WHERE project_id = ?",
                (project_id,),
            )
            session_count = cursor.fetchone()[0]

            # Count total messages
            cursor.execute(
                """
                SELECT COUNT(*) FROM project_chat_messages
                WHERE session_id IN (
                    SELECT id FROM project_chat_sessions WHERE project_id = ?
                )
                """,
                (project_id,),
            )
            message_count = cursor.fetchone()[0]

            return {
                "context_count": context_count,
                "session_count": session_count,
                "message_count": message_count,
            }
