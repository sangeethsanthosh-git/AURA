"""Bounded page retrieval and content extraction."""

from __future__ import annotations

import html
import gzip
import zlib
import logging
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from backend.web.models import RetrievedPage, SearchResult

LOGGER = logging.getLogger(__name__)


class PageRetriever:
    def __init__(self, timeout: int = 15, max_content_size: int = 120_000, max_download_size: int = 1_000_000) -> None:
        self.timeout = timeout
        self.max_content_size = max_content_size
        self.max_download_size = max_download_size

    def retrieve(self, result: SearchResult) -> RetrievedPage:
        parsed = urlparse(result.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return RetrievedPage(result, False, error="Invalid URL.")
        try:
            request = Request(result.url, headers={"User-Agent": "AURA-Web-Intelligence/1.0", "Accept-Encoding": "gzip, deflate, identity"})
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read(self.max_download_size + 1)
                status_code = response.status
                encoding = response.headers.get("Content-Encoding", "")
            raw = self._decode_body(raw, encoding)
            if len(raw) > self.max_content_size:
                raw = raw[: self.max_content_size]
            text = raw.decode("utf-8", errors="replace")
            content = self.extract_content(text)
            if not content:
                return RetrievedPage(result, False, status_code=status_code, error="No useful page content extracted.")
            return RetrievedPage(result, True, content[: self.max_content_size], status_code=status_code)
        except HTTPError as exc:
            return RetrievedPage(result, False, status_code=exc.code, error=f"HTTP error {exc.code}")
        except (URLError, TimeoutError) as exc:
            return RetrievedPage(result, False, error=f"Network error: {exc}")

    @staticmethod
    def extract_content(raw: str) -> str:
        text = re.sub(r"(?is)<(script|style|noscript|svg).*?>.*?</\1>", " ", raw)
        text = re.sub(r"(?is)<nav.*?>.*?</nav>|<footer.*?>.*?</footer>|<header.*?>.*?</header>", " ", text)
        text = re.sub(r"(?is)<br\s*/?>|</p>|</h[1-6]>|</li>", "\n", text)
        text = re.sub(r"(?is)<.*?>", " ", text)
        text = html.unescape(text)
        lines = [" ".join(line.split()) for line in text.splitlines()]
        useful = [line for line in lines if len(line) > 40]
        if useful:
            return "\n".join(useful[:80])
        compact = [line for line in lines if line]
        return "\n".join(compact[:160])

    @staticmethod
    def _decode_body(raw: bytes, encoding: str) -> bytes:
        lowered = encoding.lower()
        try:
            if "gzip" in lowered or raw.startswith(b"\x1f\x8b"):
                return gzip.decompress(raw)
            if "deflate" in lowered:
                return zlib.decompress(raw)
        except zlib.error:
            return raw
        except (OSError, EOFError):
            return raw
        return raw
