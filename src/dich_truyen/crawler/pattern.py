"""LLM-powered pattern discovery for chapter lists and content."""

import json
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from dich_truyen.config import LLMConfig
from dich_truyen.translator.llm import LLMClient
from dich_truyen.utils.progress import BookPatterns

logger = structlog.get_logger()


class DiscoveredBook(BaseModel):
    """Information discovered from a book index page."""

    title: str = Field(description="Book title in Chinese")
    author: str = Field(description="Author name")
    encoding: str = Field(default="utf-8", description="Page encoding")
    patterns: BookPatterns = Field(default_factory=BookPatterns)
    has_pagination: bool = Field(default=False)
    pagination_selector: Optional[str] = None


class DiscoveredChapter(BaseModel):
    """Discovered chapter information."""

    index: int
    id: str
    title: str
    url: str


PATTERN_DISCOVERY_PROMPT = """Analyze this HTML page from a Chinese novel website and extract structural information.

Page URL: {url}
HTML Content (truncated):
```html
{html}
```

Please identify:
1. Book title (书名) - look in <h1>, <title>, or common patterns
2. Author name (作者) - look for "作者：" or "作    者：" pattern
3. CSS selector that matches ALL chapter links (must be specific to chapter list only)
4. Content encoding from meta tags
5. Any pagination (分页) for chapter list

Return ONLY valid JSON (no markdown, no explanation):
{{
    "title": "书名",
    "author": "作者名",
    "chapter_selector": ".centent ul li a",
    "encoding": "gbk",
    "has_pagination": false,
    "pagination_selector": null
}}
"""

CHAPTER_PATTERN_PROMPT = """Analyze this chapter page from a Chinese novel website.

Page URL: {url}
HTML Content (truncated):
```html
{html}
```

Identify:
1. CSS selector for chapter title
2. CSS selector for chapter content
3. Elements to remove (ads, navigation, scripts)

Return ONLY valid JSON:
{{
    "title_selector": "h1",
    "content_selector": "#content",
    "elements_to_remove": ["script", "style", ".toplink", "table"]
}}
"""


class PatternDiscovery:
    """LLM-powered pattern extraction for chapter lists."""

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        """Initialize pattern discovery.

        Args:
            llm_config: LLM configuration, uses crawler_llm config if None
        """
        # Use LLMClient with task="crawl" for automatic config lookup
        self._llm = LLMClient(config=llm_config, task="crawl")
        self.config = self._llm.config

    @property
    def client(self):
        """Get OpenAI client from LLMClient."""
        return self._llm.client

    async def analyze_index_page(self, html: str, url: str) -> DiscoveredBook:
        """Use LLM to discover book info and chapter list pattern.

        Args:
            html: HTML content of the index page
            url: URL of the page

        Returns:
            Discovered book information
        """
        # Truncate HTML to avoid token limits
        soup = BeautifulSoup(html, "lxml")

        # Remove script and style tags for cleaner analysis
        for tag in soup(["script", "style"]):
            tag.decompose()

        truncated_html = str(soup)[:15000]

        prompt = PATTERN_DISCOVERY_PROMPT.format(url=url, html=truncated_html)

        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert at analyzing HTML structure."
                        " Return only valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Low temperature for more deterministic output
            max_tokens=500,
        )

        result_text = response.choices[0].message.content

        # Handle None content
        if result_text is None:
            logger.warning("llm_empty_response", page="index")
            result_text = "{}"

        result_text = result_text.strip()

        # Try to extract JSON from response
        result = self._parse_json_response(result_text)

        logger.debug(
            "index_page_analysis",
            chapter_selector=result.get("chapter_selector", "a"),
            encoding=result.get("encoding", "utf-8"),
            has_pagination=result.get("has_pagination", False),
        )

        return DiscoveredBook(
            title=result.get("title", "Unknown"),
            author=result.get("author", "Unknown"),
            encoding=result.get("encoding", "utf-8"),
            patterns=BookPatterns(
                chapter_selector=result.get("chapter_selector", "a"),
            ),
            has_pagination=result.get("has_pagination", False),
            pagination_selector=result.get("pagination_selector"),
        )

    async def analyze_chapter_page(self, html: str, url: str) -> BookPatterns:
        """Use LLM to discover chapter content structure.

        Args:
            html: HTML content of a chapter page
            url: URL of the page

        Returns:
            Updated patterns with content selectors
        """
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style"]):
            tag.decompose()

        truncated_html = str(soup)[:15000]

        # Debug: Log HTML size
        logger.debug(
            "chapter_page_html", original_size=len(html), truncated_size=len(truncated_html)
        )

        prompt = CHAPTER_PATTERN_PROMPT.format(url=url, html=truncated_html)

        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing HTML structure. Return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=300,
        )

        result_text = response.choices[0].message.content

        logger.debug(
            "llm_chapter_response",
            finish_reason=response.choices[0].finish_reason,
            content_is_none=(result_text is None),
        )
        if result_text:
            logger.debug("llm_chapter_preview", preview=result_text[:100])

        # Handle None content
        if result_text is None:
            logger.warning("llm_empty_response", page="chapter")
            result_text = "{}"

        result_text = result_text.strip()
        result = self._parse_json_response(result_text)

        # Log extracted patterns
        title_sel = result.get("title_selector", "h1")
        content_sel = result.get("content_selector", "#content")
        remove_els = result.get("elements_to_remove", ["script", "style", ".toplink", "table"])

        logger.debug(
            "chapter_page_analysis",
            title_selector=title_sel,
            content_selector=content_sel,
            elements_to_remove=remove_els,
        )

        return BookPatterns(
            title_selector=title_sel,
            content_selector=content_sel,
            elements_to_remove=remove_els,
        )

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Try direct JSON parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding JSON object in text
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

        return {}

    def extract_chapters_from_html(
        self, html: str, base_url: str, selector: str
    ) -> list[DiscoveredChapter]:
        """Extract chapter list from HTML using discovered selector.

        Args:
            html: HTML content of index page
            base_url: Base URL for resolving relative links
            selector: CSS selector for chapter links

        Returns:
            List of discovered chapters
        """
        soup = BeautifulSoup(html, "lxml")
        links = soup.select(selector)

        chapters = []
        seen_urls = set()

        for i, link in enumerate(links, start=1):
            href = link.get("href", "")
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            # Resolve relative URLs
            full_url = urljoin(base_url, href)

            # Skip duplicates
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Extract chapter ID from URL
            chapter_id = self._extract_chapter_id(href)

            chapters.append(
                DiscoveredChapter(
                    index=len(chapters) + 1,
                    id=chapter_id,
                    title=link.get_text(strip=True),
                    url=full_url,
                )
            )

        return chapters

    def _extract_chapter_id(self, href: str) -> str:
        """Extract chapter ID from URL path."""
        # Try to extract numeric ID from URL like "5588734.html"
        match = re.search(r"(\d+)\.html?$", href)
        if match:
            return match.group(1)

        # Fallback to the path component
        parsed = urlparse(href)
        path = parsed.path.rstrip("/")
        return path.split("/")[-1] if path else href

    def extract_chapter_content(self, html: str, patterns: BookPatterns) -> tuple[str, str]:
        """Extract title and content from chapter page.

        Args:
            html: HTML content of chapter page
            patterns: Extraction patterns

        Returns:
            Tuple of (title, content)
        """
        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title_elem = soup.select_one(patterns.title_selector)
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Remove unwanted elements from the whole document first
        for selector in patterns.elements_to_remove:
            if selector:  # Skip empty selectors
                try:
                    for elem in soup.select(selector):
                        elem.decompose()
                except Exception:
                    pass  # Skip invalid selectors

        # Try to extract content with the specified selector
        content_elem = soup.select_one(patterns.content_selector)

        if content_elem:
            content = self._extract_text_with_breaks(content_elem)
            # Check if we got meaningful content (more than just whitespace)
            if len(content.strip()) > 100:
                return title, content

        # Fallback: if content selector failed or got too little content,
        # try extracting from body directly (common for some Chinese novel sites)
        body = soup.find("body")
        if body:
            # Remove navigation, header, footer-like elements
            for tag in body.find_all(["header", "footer", "nav", "aside"]):
                tag.decompose()

            # Remove the title element to avoid duplication
            if title_elem:
                try:
                    title_elem.decompose()
                except Exception:
                    pass

            content = self._extract_text_with_breaks(body)

            # Clean up common navigation text patterns
            content_lines = content.split("\n\n")
            filtered_lines = []
            for line in content_lines:
                # Skip short lines that are likely navigation
                if len(line.strip()) < 10:
                    continue
                # Skip common navigation patterns
                if any(nav in line for nav in ["上一章", "下一章", "目录", "返回", "首页"]):
                    continue
                filtered_lines.append(line)

            content = "\n\n".join(filtered_lines)

        return title, content

    def _extract_text_with_breaks(self, element) -> str:
        """Extract text from element, preserving paragraph breaks."""
        # Replace <br> with newlines
        for br in element.find_all("br"):
            br.replace_with("\n")

        # Replace <p> with double newlines
        for p in element.find_all("p"):
            p.insert_after("\n\n")

        # Get text and clean up
        text = element.get_text()

        # Normalize whitespace but preserve paragraph breaks
        lines = []
        for line in text.split("\n"):
            line = " ".join(line.split())  # Normalize whitespace within line
            if line:
                lines.append(line)

        return "\n\n".join(lines)
