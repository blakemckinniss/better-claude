#!/usr/bin/env python3
"""Firecrawl web search and scraping integration for enhanced context."""

import asyncio
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from UserPromptSubmit.config import get_config
from UserPromptSubmit.http_session_manager import (
    HTTPSessionManager,
    get_compiled_pattern,
)


class FirecrawlClient:
    """Async client for Firecrawl API integration."""

    def __init__(self):
        self.config = get_config().firecrawl
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

    async def search(
        self,
        query: str,
        limit: int = 3,
        location: str = "",
        tbs: str = "",
        formats: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Search the web using Firecrawl."""
        if formats is None:
            formats = ["markdown"]

        payload = {
            "query": query,
            "limit": limit or self.config.search_limit,
            "location": location,
            "tbs": tbs,
            "scrapeOptions": {"formats": formats},
        }

        try:
            async with HTTPSessionManager.request(
                "POST",
                f"{self.config.base_url}/search",
                headers=self.headers,
                json=payload,
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
        except Exception:
            return None

    async def scrape(
        self,
        url: str,
        formats: Optional[List[str]] = None,
        only_main_content: bool = True,
        parse_pdf: bool = True,
        max_age: int = 14400000,
    ) -> Optional[Dict[str, Any]]:
        """Scrape a URL using Firecrawl."""
        if formats is None:
            formats = ["markdown"]

        payload = {
            "url": url,
            "formats": formats,
            "onlyMainContent": only_main_content,
            "parsePDF": parse_pdf,
            "maxAge": max_age,
        }

        try:
            async with HTTPSessionManager.request(
                "POST",
                f"{self.config.base_url}/scrape",
                headers=self.headers,
                json=payload,
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
        except Exception:
            return None


class FirecrawlAnalyzer:
    """Analyze user prompts to determine if web search would be beneficial."""

    # Patterns that suggest web search would be helpful
    WEB_SEARCH_PATTERNS = [
        # Current information requests
        r"\b(latest|current|recent|new|2024|2025|today|now)\b",
        r"\b(what's|whats|what is|tell me about)\s+(?:the\s+)?(?:latest|current|new)\b",
        # Best practices and trends
        r"\b(best\s+practices?|trends?|popular|recommended|state\s+of\s+the\s+art)\b",
        r"\b(how\s+to\s+(?:properly|correctly|effectively))\b",
        # Documentation and tutorials
        r"\b(documentation|docs|tutorial|guide|examples?|samples?)\b",
        r"\b(how\s+to\s+(?:use|implement|setup|configure|install))\b",
        # Technology and tool queries
        r"\b(framework|library|package|tool|api|service|platform)\b.*\b(comparison|vs|versus|alternative)\b",
        r"\b(github|npm|pypi|documentation|official\s+site)\b",
        # Problem solving
        r"\b(error|issue|problem|bug|troubleshoot|fix|solve)\b.*\b(with|in|when|using)\b",
        r"\b(stack\s+overflow|community|forum|discussion)\b",
        # Learning and explanation requests
        r"\b(explain|understand|learn|teach me|show me)\b",
        r"\b(difference\s+between|compare|contrast)\b",
    ]

    # Patterns that suggest specific URLs should be scraped
    URL_SCRAPE_PATTERNS = [
        r"https?://[^\s]+",  # Any URL in the prompt
        r"\b(check|read|analyze|scrape)\s+(?:this\s+)?(?:url|link|page|site|website)\b",
    ]

    # Technology-specific search queries
    TECH_QUERIES = {
        "python": "python best practices documentation examples",
        "javascript": "javascript modern best practices examples",
        "react": "react latest patterns documentation",
        "node": "nodejs best practices documentation",
        "docker": "docker best practices configuration examples",
        "kubernetes": "kubernetes deployment examples documentation",
        "aws": "aws best practices configuration examples",
        "git": "git workflow best practices documentation",
    }

    @classmethod
    def should_use_web_search(cls, prompt: str) -> bool:
        """Determine if web search would be beneficial for this prompt."""
        prompt_lower = prompt.lower()

        # Check for web search indicators
        for pattern in cls.WEB_SEARCH_PATTERNS:
            if re.search(pattern, prompt_lower):
                return True

        return False

    @classmethod
    def extract_urls(cls, prompt: str) -> List[str]:
        """Extract URLs from the prompt for scraping."""
        url_pattern = get_compiled_pattern("url_pattern")
        urls = url_pattern.findall(prompt)

        # Clean URLs (remove trailing punctuation)
        cleaned_urls = []
        for url in urls:
            cleaned = re.sub(r"[.,:;!?)\]}>]+$", "", url)
            cleaned_urls.append(cleaned)

        return cleaned_urls

    @classmethod
    def generate_search_query(cls, prompt: str) -> str:
        """Generate an optimized search query from the user prompt."""
        prompt_lower = prompt.lower()

        # Check for technology-specific queries
        for tech, query in cls.TECH_QUERIES.items():
            if tech in prompt_lower:
                # Extract specific terms from prompt
                tech_terms = re.findall(rf"\b{tech}[a-z]*\b", prompt_lower)
                if tech_terms:
                    return f"{query} {' '.join(tech_terms)}"

        # Extract key terms from prompt
        # Remove common words and focus on technical terms
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "how",
            "what",
            "when",
            "where",
            "why",
            "can",
            "could",
            "should",
            "would",
            "will",
            "do",
            "does",
            "did",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
        }

        # Extract meaningful terms
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]*\b", prompt)
        meaningful_words = [
            word for word in words if len(word) > 2 and word.lower() not in stop_words
        ]

        # Prioritize technical terms
        technical_patterns = [
            r"\b[A-Z][a-z]+[A-Z][a-z]*\b",  # CamelCase
            r"\b[a-z]+_[a-z]+\b",  # snake_case
            r"\b[a-z]+-[a-z]+\b",  # kebab-case
            r"\b\w+\.\w+\b",  # dotted notation
        ]

        tech_terms = []
        for pattern in technical_patterns:
            tech_terms.extend(re.findall(pattern, prompt))

        # Combine and prioritize
        key_terms = list(set(tech_terms + meaningful_words[:10]))

        # Create search query
        if len(key_terms) > 0:
            base_query = " ".join(key_terms[:8])  # Limit to 8 terms

            # Add context terms based on prompt patterns
            if re.search(r"\b(best\s+practices?|how\s+to)\b", prompt_lower):
                base_query += " best practices examples"
            elif re.search(r"\b(error|issue|problem|bug)\b", prompt_lower):
                base_query += " troubleshooting solution"
            elif re.search(r"\b(documentation|docs|guide)\b", prompt_lower):
                base_query += " official documentation"

            return base_query

        # Fallback to first 100 characters of prompt
        return prompt[:100].strip()


async def get_firecrawl_injection(prompt: str, project_dir: str) -> str:
    """Main entry point for Firecrawl web search and scraping injection."""
    api_key = os.environ.get("FIRECRAWL_API_KEY")

    if not api_key:
        return ""  # Skip if no API key configured

    analyzer = FirecrawlAnalyzer()

    # Check if web search would be beneficial
    should_search = analyzer.should_use_web_search(prompt)
    urls_to_scrape = analyzer.extract_urls(prompt)

    if not should_search and not urls_to_scrape:
        return ""

    client = FirecrawlClient()
    injection_parts = ["<firecrawl-context>"]

    try:
        # Perform web search if beneficial
        if should_search:
            search_query = analyzer.generate_search_query(prompt)
            search_results = await client.search(search_query)

            if search_results and search_results.get("data"):
                injection_parts.append(f"Web search for: {search_query}")

                for idx, result in enumerate(search_results["data"][:3], 1):
                    url = result.get("url", "Unknown URL")
                    title = result.get("title", "No title")
                    content = result.get("markdown", result.get("content", ""))

                    # Limit content to prevent token explosion
                    if content and len(content) > 1000:
                        content = f"{content[:1000]}..."

                    injection_parts.append(f"Result {idx}: {title}")
                    injection_parts.append(f"URL: {url}")
                    if content:
                        injection_parts.append(f"Content:\n{content}")
                    injection_parts.append("")  # Separator

        # Scrape specific URLs mentioned in prompt
        if urls_to_scrape:
            injection_parts.append("URL scraping results:")

            # Limit to 3 URLs to prevent excessive data
            for url in urls_to_scrape[: client.config.url_limit]:
                try:
                    # Validate URL
                    parsed = urlparse(url)
                    if parsed.scheme not in ("http", "https"):
                        continue

                    scrape_result = await client.scrape(url)

                    if scrape_result and scrape_result.get("data"):
                        data = scrape_result["data"]
                        title = data.get("title", "No title")
                        content = data.get("markdown", data.get("content", ""))

                        # Limit content
                        if content and len(content) > client.config.content_limit:
                            content = f"{content[:client.config.content_limit]}..."

                        injection_parts.append(f"Scraped: {title}")
                        injection_parts.append(f"URL: {url}")
                        if content:
                            injection_parts.append(f"Content:\n{content}")
                        injection_parts.append("")  # Separator

                except Exception:
                    # Skip individual URL failures
                    continue

        injection_parts.append("</firecrawl-context>")

        # Only return injection if we have meaningful content
        if len(injection_parts) > 2:  # More than just opening/closing tags
            return f"{'\n'.join(injection_parts)}\n"

    except Exception:
        # Don't let Firecrawl errors break the hook
        pass

    return ""


if __name__ == "__main__":
    # Test the injection
    import sys

    test_prompt = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "What are the latest React best practices?"
    )
    project_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

    async def test():
        result = await get_firecrawl_injection(test_prompt, project_dir)
        print(result, file=sys.stderr)

    asyncio.run(test())
