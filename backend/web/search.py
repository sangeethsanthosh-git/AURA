"""Replaceable web search providers."""

from __future__ import annotations

import html
import json
import logging
import re
from urllib.parse import quote_plus, unquote, urlparse, parse_qs
from urllib.request import Request, urlopen

from backend.web.models import SearchResult

LOGGER = logging.getLogger(__name__)


class SearchProvider:
    provider_name = "Search Provider"

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        raise NotImplementedError


class DuckDuckGoHtmlSearchProvider(SearchProvider):
    """Small no-key search provider using DuckDuckGo's HTML endpoint."""

    provider_name = "DuckDuckGo HTML"
    SEARCH_URL = "https://duckduckgo.com/html/?q="

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        url = self.SEARCH_URL + quote_plus(query)
        request = Request(url, headers={"User-Agent": "AURA-Web-Intelligence/1.0"})
        with urlopen(request, timeout=self.timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
        return self._parse(body, limit)

    def _parse(self, body: str, limit: int) -> list[SearchResult]:
        results: list[SearchResult] = []
        blocks = re.findall(r'<a rel="nofollow" class="result__a" href="(?P<href>.*?)".*?>(?P<title>.*?)</a>(?P<rest>.*?)(?=<a rel="nofollow" class="result__a"|$)', body, flags=re.DOTALL)
        for href, title_html, rest in blocks:
            clean_url = self._clean_duck_url(html.unescape(href))
            title = self._strip_tags(title_html)
            snippet_match = re.search(r'class="result__snippet".*?>(.*?)</a>', rest, flags=re.DOTALL)
            snippet = self._strip_tags(snippet_match.group(1)) if snippet_match else ""
            if clean_url and title:
                results.append(SearchResult(title, clean_url, snippet, urlparse(clean_url).netloc, relevance=1.0 / (len(results) + 1)))
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def _clean_duck_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
            uddg = parse_qs(parsed.query).get("uddg", [""])[0]
            return unquote(uddg)
        return url

    @staticmethod
    def _strip_tags(value: str) -> str:
        text = re.sub(r"<.*?>", " ", value)
        return " ".join(html.unescape(text).split())


class WikipediaSearchProvider(SearchProvider):
    provider_name = "Wikipedia Search"
    API_URL = "https://en.wikipedia.org/w/api.php"

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        params = (
            "action=query&list=search&format=json&utf8=1"
            f"&srlimit={limit}&srsearch={quote_plus(query)}"
        )
        request = Request(f"{self.API_URL}?{params}", headers={"User-Agent": "AURA-Web-Intelligence/1.0"})
        with urlopen(request, timeout=self.timeout) as response:
            raw = json.loads(response.read().decode("utf-8", errors="replace"))
        results = []
        for index, item in enumerate(raw.get("query", {}).get("search", [])[:limit], start=1):
            title = str(item.get("title") or "")
            if not title:
                continue
            url = "https://en.wikipedia.org/wiki/" + quote_plus(title.replace(" ", "_"))
            results.append(
                SearchResult(
                    title,
                    url,
                    self._strip_tags(str(item.get("snippet") or "")),
                    "en.wikipedia.org",
                    relevance=1.0 / index,
                )
            )
        return results

    @staticmethod
    def _strip_tags(value: str) -> str:
        return DuckDuckGoHtmlSearchProvider._strip_tags(value)


class OfficialKnownSourceProvider(SearchProvider):
    provider_name = "Official Known Sources"

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        lowered = query.lower()
        results: list[SearchResult] = []
        if "python" in lowered and any(term in lowered for term in ("release", "version", "latest", "current")):
            results.extend(
                [
                    SearchResult(
                        "Python Windows Recent Release Index",
                        "https://www.python.org/ftp/python/index-windows-recent.json",
                        "Official Python recent release index.",
                        "python.org",
                        relevance=1.0,
                    ),
                    SearchResult(
                        "Python Downloads",
                        "https://www.python.org/downloads/",
                        "Official Python downloads page.",
                        "python.org",
                        relevance=0.9,
                    ),
                    SearchResult(
                        "Python Release History",
                        "https://www.python.org/downloads/source/",
                        "Official Python source release history.",
                        "python.org",
                        relevance=0.8,
                    ),
                ]
            )
        return results[:limit]


class CompositeSearchProvider(SearchProvider):
    provider_name = "Composite Web Search"

    def __init__(self, providers: list[SearchProvider] | None = None) -> None:
        self.providers = providers or [OfficialKnownSourceProvider(), DuckDuckGoHtmlSearchProvider(), WikipediaSearchProvider()]

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        last_error: Exception | None = None
        for provider in self.providers:
            try:
                results = provider.search(query, limit)
                if results:
                    return results[:limit]
            except Exception as exc:
                last_error = exc
                LOGGER.warning("Search provider failed: %s", provider.provider_name)
        if last_error:
            raise last_error
        return []
