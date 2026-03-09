"""
URL Processor - Extract clean text from web articles for TTS
Uses archive.is to bypass paywalls/JS, then readability for extraction.
"""

import archiveis
from readability import Document
import requests
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import hashlib
import json
import time
from loguru import logger
import threading
import queue


class URLProcessor:
    """
    Processes web articles with two-pass cleaning:
    1. archive.is captures the page (removes JS, paywalls)
    2. readability extracts clean text content
    """

    def __init__(self, timeout: int = 30, user_agent: Optional[str] = None):
        """
        Initialize URL processor

        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
        """
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # Statistics
        self.stats = {
            "processed": 0,
            "archive_success": 0,
            "extraction_success": 0,
            "failures": 0,
        }

        logger.info("URLProcessor initialized")

    def process(
        self, url: str, progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Process a URL and return clean article content

        Args:
            url: The article URL to process
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with:
                - title: Article title
                - content: Clean text content
                - url: Original URL
                - archive_url: archive.is URL
                - metadata: Additional metadata

        Raises:
            Exception: If processing fails
        """
        try:
            if progress_callback:
                progress_callback("🌐 Contacting archive.is...")

            # Step 1: Archive the URL
            logger.info(f"Archiving URL: {url}")
            archive_url = archiveis.capture(url)
            self.stats["archive_success"] += 1
            logger.info(f"Archived to: {archive_url}")

            if progress_callback:
                progress_callback("📥 Fetching archived version...")

            # Step 2: Fetch archived HTML
            response = requests.get(
                archive_url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
            )
            response.raise_for_status()
            html = response.text

            if progress_callback:
                progress_callback("🔍 Extracting article content...")

            # Step 3: Extract with readability
            doc = Document(html, url=archive_url)
            title = doc.title()
            content_html = doc.summary()

            # Convert HTML to plain text
            content = self._html_to_text(content_html)

            # Validate content
            if not content or len(content.strip()) < 100:
                raise ValueError("Extracted content too short - may not be an article")

            self.stats["extraction_success"] += 1
            self.stats["processed"] += 1

            if progress_callback:
                progress_callback(f"✅ Extracted: {len(content)} chars")

            # Build result
            result = {
                "type": "article",
                "title": title,
                "content": content,
                "url": url,
                "archive_url": archive_url,
                "metadata": {
                    "provider": "url_processor",
                    "timestamp": time.time(),
                    "content_length": len(content),
                    "word_count": len(content.split()),
                },
            }

            return result

        except Exception as e:
            self.stats["failures"] += 1
            logger.warning(f"archive.is failed, trying direct fetch: {e}")

            # Fallback: try direct fetch
            if progress_callback:
                progress_callback("Trying direct fetch...")

            try:
                return self._process_direct(url, progress_callback)
            except Exception as direct_error:
                logger.error(f"Direct fetch also failed: {direct_error}")
                raise Exception(f"Failed to process URL: {direct_error}")

    def process_async(
        self,
        url: str,
        result_queue: queue.Queue,
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Process URL asynchronously (non-blocking)

        Args:
            url: URL to process
            result_queue: Queue to put results in
            progress_callback: Optional progress callback
        """

        def _run():
            try:
                result = self.process(url, progress_callback)
                result_queue.put(("success", result))
            except Exception as e:
                result_queue.put(("error", str(e)))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def _process_direct(
        self,
        url: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Fallback: directly fetch URL without archive.is
        Used when archive.is is rate limited
        """
        if progress_callback:
            progress_callback("📥 Fetching URL directly...")

        # Fetch the URL directly
        response = requests.get(
            url,
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
            verify=False,  # Bypass SSL for sites with cert issues
        )
        response.raise_for_status()
        html = response.text

        if progress_callback:
            progress_callback("🔍 Extracting article content...")

        # Extract with readability
        doc = Document(html, url=url)
        title = doc.title()
        content_html = doc.summary()

        # Convert HTML to plain text
        content = self._html_to_text(content_html)

        # Validate content
        if not content or len(content.strip()) < 100:
            raise ValueError("Extracted content too short - may not be an article")

        self.stats["extraction_success"] += 1
        self.stats["processed"] += 1

        if progress_callback:
            progress_callback(f"✅ Extracted: {len(content)} chars")

        # Build result
        result = {
            "type": "article",
            "title": title,
            "content": content,
            "url": url,
            "archive_url": None,  # No archive used
            "metadata": {
                "provider": "url_processor",
                "method": "direct",
                "timestamp": time.time(),
                "content_length": len(content),
                "word_count": len(content.split()),
            },
        }

        return result

    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to clean plain text

        Args:
            html: HTML content

        Returns:
            Clean plain text
        """
        from bs4 import BeautifulSoup
        import re

        soup = BeautifulSoup(html, "lxml")

        # Remove unwanted elements
        for element in soup.find_all(
            ["script", "style", "nav", "header", "footer", "aside"]
        ):
            element.decompose()

        # Get text with proper spacing
        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)  # Multiple newlines to double
        text = re.sub(r" +", " ", text)  # Multiple spaces to single
        text = text.strip()

        return text

    def get_stats(self) -> Dict[str, int]:
        """Get processor statistics"""
        return self.stats.copy()
