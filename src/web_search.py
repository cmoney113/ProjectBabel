"""
Web Search Manager for Canary Voice AI Assistant
Handles Tavily API integration for current events and comprehensive information
"""

from tavily import TavilyClient
import re
from typing import Optional, List


# Alias for backward compatibility
class TavilySearch:
    """Simple wrapper for TavilyClient for easy instantiation"""
    
    def __init__(self, api_key: str):
        self.client = TavilyClient(api_key=api_key)
    
    def search(self, query: str, max_results: int = 5):
        """Perform search and return results"""
        return self.client.search(
            query=query,
            search_depth="advanced",
            include_answer=True,
            max_results=max_results
        )


class WebSearchManager:
    """Manages web search functionality with Tavily API"""
    
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        tavily_config = self.settings_manager.get_tavily_config()
        self.tavily_client = TavilyClient(api_key=tavily_config["api_key"])
        
    def should_perform_search(self, query: str, confidence_threshold: float = 0.85) -> bool:
        """Determine if a web search should be performed"""
        # Check for current events keywords
        current_events_keywords = [
            'today', 'yesterday', 'tomorrow', 'current', 'latest', 'recent', 
            'news', 'breaking', 'update', '2024', '2025', '2026', 'this week',
            'this month', 'this year', 'now', 'currently', 'happening'
        ]
        
        query_lower = query.lower()
        
        # Check if query contains current events keywords
        if any(keyword in query_lower for keyword in current_events_keywords):
            return True
            
        # Check if query is asking for comprehensive information
        comprehensive_keywords = [
            'explain', 'how does', 'what is', 'tell me about', 'describe',
            'comprehensive', 'detailed', 'thorough', 'complete guide',
            'everything about', 'all about', 'overview of'
        ]
        
        if any(keyword in query_lower for keyword in comprehensive_keywords):
            return True
            
        # Check if query is beyond common knowledge
        common_knowledge_indicators = [
            'what color', 'how many', 'who is', 'when was', 'where is',
            'simple', 'basic', 'easy', 'quick', 'short'
        ]
        
        # If it's clearly common knowledge, don't search
        if any(indicator in query_lower for indicator in common_knowledge_indicators):
            return False
            
        # Default: search for anything that might need up-to-date or comprehensive info
        return True
        
    def search(self, query: str, max_results: int = 5) -> str:
        """Perform web search using Tavily API"""
        try:
            response = self.tavily_client.search(
                query=query,
                search_depth="advanced",
                include_answer=True,
                max_results=max_results
            )
            
            # Format results for LLM context
            formatted_results = self._format_search_results(response)
            return formatted_results
            
        except Exception as e:
            print(f"Web search error: {e}")
            return f"Web search failed: {str(e)}"
            
    def _format_search_results(self, response: dict) -> str:
        """Format search results for LLM context"""
        if not response or 'results' not in response:
            return "No relevant search results found."
            
        formatted = "Web Search Results:\n\n"
        
        # Add answer if available
        if 'answer' in response and response['answer']:
            formatted += f"Summary: {response['answer']}\n\n"
            
        # Add individual results
        for i, result in enumerate(response.get('results', []), 1):
            formatted += f"Result {i}:\n"
            formatted += f"Title: {result.get('title', 'No title')}\n"
            formatted += f"Content: {result.get('content', 'No content')}\n"
            formatted += f"URL: {result.get('url', 'No URL')}\n\n"
            
        return formatted.strip()
        
    def extract_entities(self, text: str) -> List[str]:
        """Extract potential entities from text for targeted search"""
        # Simple entity extraction - in practice, this would use NER
        entities = []
        
        # Extract potential proper nouns (capitalized words)
        words = text.split()
        for word in words:
            if word[0].isupper() and len(word) > 2:
                entities.append(word)
                
        # Extract dates
        date_patterns = [
            r'\b\d{4}\b',  # Years
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend(matches)
            
        return list(set(entities))  # Remove duplicates