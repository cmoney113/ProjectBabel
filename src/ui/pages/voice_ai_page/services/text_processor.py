"""
Text Processor Service
Handles URL processing, web search, and text analysis
"""

import re
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TextProcessorService:
    """Service for processing text, URLs, and search queries"""

    def __init__(self, settings_manager=None):
        self.settings_manager = settings_manager

    def is_url(self, text: str) -> bool:
        """
        Check if text is a URL

        Args:
            text: Text to check

        Returns:
            True if text looks like a URL
        """
        url_pattern = re.compile(
            r"^(https?://)?"
            r"(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
            r"(?::\d+)?"
            r"(?:/|$|#|\?)",
            re.IGNORECASE,
        )
        return bool(url_pattern.match(text)) or text.startswith(
            ("http://", "https://")
        )

    def normalize_url(self, text: str) -> str:
        """
        Normalize URL by adding https:// if missing

        Args:
            text: URL text

        Returns:
            Normalized URL with protocol
        """
        if self.is_url(text) and not text.startswith(("http://", "https://")):
            return f"https://{text}"
        return text

    def is_search_query(self, text: str) -> bool:
        """
        Check if text looks like a search query

        Args:
            text: Text to check

        Returns:
            True if text looks like a search query
        """
        text = text.strip().lower()

        # Not a URL
        if self.is_url(text):
            return False

        # Not a command (starts with /)
        if text.startswith("/"):
            return False

        # Check for search indicators
        search_indicators = [
            "?",
            "how",
            "what",
            "why",
            "when",
            "where",
            "who",
            "which",
            "latest",
            "news",
            "search",
        ]
        is_search = any(indicator in text for indicator in search_indicators)

        # Also treat plain multi-word text as search if it doesn't look like a sentence
        if not is_search and len(text.split()) >= 2:
            if "." not in text and "/" not in text:
                is_search = True

        return is_search

    def process_url(
        self, url: str, progress_callback=None
    ) -> Optional[dict]:
        """
        Process URL through archive.is and extract content

        Args:
            url: URL to process
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with 'title' and 'content' keys, or None on failure
        """
        from src.url_processor import URLProcessor

        try:
            processor = URLProcessor()

            def callback(msg: str):
                if progress_callback:
                    progress_callback(msg)

            result = processor.process(url, progress_callback=callback)
            return {
                "title": result.get("title", "Article"),
                "content": result.get("content", ""),
            }
        except Exception as e:
            logger.error(f"URL processing failed: {e}")
            return None

    def run_web_search(
        self, query: str, max_results: int = 5
    ) -> list[dict]:
        """
        Run web search using Tavily API

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of search result dicts with 'title', 'url', 'content'
        """
        from src.web_search import TavilySearch

        # Get API key
        api_key = os.environ.get("TAVILY_API_KEY", "")
        if not api_key and self.settings_manager:
            api_key = self.settings_manager.get("tavily_api_key", "")

        if not api_key:
            logger.warning("No Tavily API key found")
            return []

        try:
            search = TavilySearch(api_key=api_key)
            results = search.search(query, max_results=max_results)
            return results.get("results", [])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def classify_text_input(self, text: str) -> str:
        """
        Classify text input type

        Args:
            text: Text to classify

        Returns:
            One of: 'url', 'search', 'plain'
        """
        if not text or not text.strip():
            return "plain"

        text = text.strip()

        if self.is_url(text):
            return "url"

        if self.is_search_query(text):
            return "search"

        return "plain"
