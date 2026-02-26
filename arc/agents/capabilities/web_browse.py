"""
WebBrowse capability — Selenium + BeautifulSoup web agent.
Ported from Jayu's google.py with ADK tool wrapping.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger("arc.capabilities.web")

try:
    from bs4 import BeautifulSoup
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    _SELENIUM_AVAILABLE = True
except ImportError:
    _SELENIUM_AVAILABLE = False
    logger.warning("Selenium/BS4 not available — web browsing disabled")


def _build_driver() -> Optional["webdriver.Chrome"]:
    if not _SELENIUM_AVAILABLE:
        return None
    opts = Options()
    opts.add_experimental_option("detach", True)
    opts.add_argument("--log-level=3")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    try:
        return webdriver.Chrome(options=opts)
    except Exception as e:
        logger.error(f"Chrome driver failed: {e}")
        return None


def extract_elements(driver, html_content: str) -> str:
    """Extract readable text + links from HTML in document order."""
    soup = BeautifulSoup(html_content, "html.parser")
    parts = [
        f"PAGE TITLE: {driver.title}\n",
        f"CURRENT URL: {driver.current_url}\n\n",
    ]
    for el in soup.descendants:
        if (
            isinstance(el, str)
            and el.strip()
            and el.parent.name not in ["script", "noscript", "template", "style"]
        ):
            parts.append(f"[TEXT <{el.parent.name}>] {el.strip()}\n")
        elif (
            el.name == "a"
            and el.has_attr("href")
            and len(el.get("href", "")) > 8
        ):
            parts.append(f"[LINK] {el.get('href')}\n")
    return "".join(parts)[:32000]  # cap at ~32k chars


class WebBrowseCapability:
    """
    Provides search_google and search_link tools for an AF agent.
    Each agent gets its own browser instance.
    """

    def __init__(self):
        self.driver: Optional["webdriver.Chrome"] = None
        self.visited_links: list[str] = []
        self._current_elements: str = ""

    def _ensure_driver(self) -> bool:
        if self.driver is None:
            self.driver = _build_driver()
        return self.driver is not None

    # ── Tool functions ────────────────────────────────────────────────────────

    def search_google(self, query: str) -> str:
        """
        Search Google with the given query.
        
        Args:
            query: Keywords to search for on Google.
        Returns:
            Extracted text and links from the search results page.
        """
        if not self._ensure_driver():
            return "Error: Browser not available."
        url = f"https://www.google.com/search?q={query}"
        logger.info(f"Google search: {query}")
        self.visited_links.append(url)
        try:
            self.driver.get(url)
            time.sleep(1.5)  # let page render
            self._current_elements = extract_elements(self.driver, self.driver.page_source)
            return self._current_elements
        except Exception as e:
            return f"Error searching Google: {e}"

    def search_link(self, url: str) -> str:
        """
        Navigate to a specific URL.
        
        Args:
            url: Full URL to navigate to (must start with http:// or https://).
        Returns:
            Extracted text and links from the page.
        """
        if not self._ensure_driver():
            return "Error: Browser not available."
        # Normalise URL
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        logger.info(f"Navigate to: {url}")
        self.visited_links.append(url)
        try:
            self.driver.get(url)
            time.sleep(1.5)
            self._current_elements = extract_elements(self.driver, self.driver.page_source)
            return self._current_elements
        except Exception as e:
            return f"Error navigating to {url}: {e}"

    def go_back(self, steps: int = 1) -> str:
        """
        Navigate back in browser history.
        
        Args:
            steps: Number of pages to go back.
        Returns:
            Extracted text and links from the resulting page.
        """
        if not self.driver:
            return "Error: No browser session."
        for _ in range(steps):
            self.driver.back()
            time.sleep(0.8)
        self._current_elements = extract_elements(self.driver, self.driver.page_source)
        return self._current_elements

    def get_current_page(self) -> str:
        """Return the current page elements without reloading."""
        return self._current_elements or "No page loaded yet."

    def get_adk_tools(self) -> list:
        """Return ADK-compatible function declarations for these tools."""
        from google.genai import types as genai_types
        return [
            genai_types.FunctionDeclaration(
                name="search_google",
                description="Search Google with keywords. Use for finding information on the web.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "query": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="Search keywords or phrase"
                        )
                    },
                    required=["query"]
                )
            ),
            genai_types.FunctionDeclaration(
                name="search_link",
                description="Navigate directly to a specific URL.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "url": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="Full URL to navigate to"
                        )
                    },
                    required=["url"]
                )
            ),
            genai_types.FunctionDeclaration(
                name="go_back",
                description="Go back N pages in browser history.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "steps": genai_types.Schema(
                            type=genai_types.Type.INTEGER,
                            description="Number of pages to go back (default 1)"
                        )
                    }
                )
            ),
        ]

    def handle_tool_call(self, name: str, args: dict) -> str:
        """Dispatch a tool call by name."""
        dispatch = {
            "search_google": lambda: self.search_google(args.get("query", "")),
            "search_link":   lambda: self.search_link(args.get("url", "")),
            "go_back":       lambda: self.go_back(args.get("steps", 1)),
        }
        fn = dispatch.get(name)
        return fn() if fn else f"Unknown web tool: {name}"

    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
