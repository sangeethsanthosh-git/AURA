"""
Service for Wikipedia Deep Search & Image Discovery.
Uses Wikipedia's public MediaWiki & REST APIs (no API keys required)
to fetch multi-article extracts and verified gallery images for deep search.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple, List, Dict
from urllib.parse import quote, urlparse
import re
import threading
import logging
import requests

from backend.config import (
    WIKIPEDIA_TIMEOUT,
    WIKIPEDIA_MAX_ARTICLES,
    WIKIPEDIA_MAX_IMAGES,
)
from backend.security.prompt_guard import prompt_guard
from backend.security.network_guard import network_guard

logger = logging.getLogger(__name__)

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
WIKI_REST_MEDIA_URL = "https://en.wikipedia.org/api/rest_v1/page/media-list"
USER_AGENT = "AURAVoiceAssistant/1.0 (local-desktop)"

# Conversational fillers / self-questions that should stay 100% local
_SKIP_PHRASES = {
    "hi",
    "hello",
    "hey",
    "hey aura",
    "hi aura",
    "hello aura",
    "thanks",
    "thank you",
    "bye",
    "goodbye",
    "ok",
    "okay",
    "yes",
    "no",
    "stop",
    "cancel",
    "how are you",
    "who are you",
    "what is your name",
    "whats your name",
    "what's your name",
    "what can you do",
    "good morning",
    "good afternoon",
    "good evening",
    "good night",
    "test",
    "testing",
}

# Explicit triggers that always invoke Wikipedia search even if auto mode is off
_EXPLICIT_TRIGGER_RE = re.compile(
    r"(?:"
    r"\b(?:search|use|check|find|look\s+up\s+on)\s+wikipedia\b|"
    r"\bwikipedia\s+(?:for|about|image|images|pictures?)?\b|"
    r"\b(?:can\s+you\s+)?(?:show|display|see|fetch)\s+(?:me\s+)?(?:the\s+|an?\s+)?(?:images?|pictures?|photos?)\b|"
    r"\b(?:images?|pictures?|photos?)\s+of\b|"
    r"\bwhat\s+does\s+(?:it|this|that)\s+look\s+like\b|"
    r"\bdeep\s+search\b"
    r")",
    re.IGNORECASE,
)

# Leading conversational question wrappers stripped to clean search terms
_QUERY_PREFIX_RE = re.compile(
    r"^\s*(?:please\s+)?(?:can you\s+|could you\s+)?"
    r"(?:search\s+wikipedia\s+(?:for|about)?|"
    r"use\s+wikipedia\s+(?:for\s+(?:images?|pictures?|photos?|info)?|about)?|"
    r"wikipedia\s+(?:for|about)?|"
    r"wiki\s+(?:for|about)?|"
    r"deep\s+search\s+(?:for|about|on)?|"
    r"(?:show|display|get|fetch)\s+(?:me\s+)?(?:the\s+|an?\s+)?(?:images?|pictures?|photos?)\s*(?:of|for|about)?|"
    r"(?:images?|pictures?|photos?)\s+of|"
    r"tell\s+me\s+(?:more\s+)?about|"
    r"facts\s+about|"
    r"history\s+of|"
    r"biography\s+of|"
    r"overview\s+of|"
    r"meaning\s+of|"
    r"look\s+up|"
    r"explain|"
    r"define|"
    r"who\s+(?:is|was|are|were)|"
    r"what\s+(?:is|was|are|were)|"
    r"where\s+(?:is|was|are)|"
    r"when\s+(?:did|was|were))\s*",
    re.IGNORECASE,
)

# Factual/encyclopedic patterns allowed to trigger automatic Wikipedia lookup
_FACTUAL_KNOWLEDGE_RE = re.compile(
    r"^\s*(?:please\s+)?(?:can you\s+|could you\s+)?"
    r"(?:who\s+(?:is|was|are|were)|"
    r"what\s+(?:is|was|are|were)|"
    r"where\s+(?:is|was|are)|"
    r"when\s+(?:did|was|were)|"
    r"tell\s+me\s+(?:more\s+)?about|"
    r"facts\s+about|"
    r"history\s+of|"
    r"biography\s+of|"
    r"overview\s+of|"
    r"meaning\s+of|"
    r"look\s+up|"
    r"define|"
    r"explain)\b",
    re.IGNORECASE,
)

# Tasks/coding/creative/personal prompts that must NEVER auto-trigger Wikipedia
_NON_WIKI_TASK_RE = re.compile(
    r"(?:^\s*(?:please\s+|can you\s+|could you\s+|help me\s+)?"
    r"(?:write|create|make|generate|build|code|program|develop|implement|design|"
    r"draft|compose|fix|debug|refactor|solve|calculate|compute|convert|translate|"
    r"summarize|rewrite|give\s+me|open|start|run|play|set|remind|list|"
    r"how\s+(?:to|do\s+i)|tell\s+me\s+(?:a|about\s+yourself))\b"
    r"|\b(?:python\s+program|xml\s+file|html\s+file|json\s+file|code\s+snippet|"
    r"function\s+to|script\s+to|program\s+to|error\s+in|bug\s+in|my\s+code|this\s+code|"
    r"your\s+name|the\s+time|the\s+date)\b)",
    re.IGNORECASE,
)

# Arithmetic-only pattern like "what is 2 + 2" or "what is 15 times 3"
_MATH_ONLY_RE = re.compile(r"^[\d\s+\-*/().%=]+$")
_HAS_MATH_WORDS_RE = re.compile(
    r"\b(?:plus|minus|times|multiplied\s+by|divided\s+by|square\s+root)\b",
    re.IGNORECASE,
)

# Wikimedia UI/chrome icons to exclude from image galleries
_ICON_BLOCKLIST = (
    "commons-logo",
    "ambox",
    "padlock",
    "question_book",
    "symbol_",
    "wiki_letter",
    "disambig",
    "edit-clear",
    "loudspeaker",
    "red_pog",
    "blue_pog",
    "gnome-",
    "nuvola_",
    "gtk-",
    "oojs_ui_icon",
    "speakerlink",
)


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _is_valid_gallery_image(title_or_url: str) -> bool:
    lower = title_or_url.lower()
    if any(token in lower for token in _ICON_BLOCKLIST):
        return False
    return True


class WikipediaService:
    def __init__(
        self,
        timeout: float = WIKIPEDIA_TIMEOUT,
        max_articles: int = WIKIPEDIA_MAX_ARTICLES,
        max_images: int = WIKIPEDIA_MAX_IMAGES,
    ):
        self.timeout = timeout
        self.max_articles = max_articles
        self.max_images = max_images
        self._thread_local = threading.local()

    def _get_session(self) -> requests.Session:
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update({"User-Agent": USER_AGENT})
            self._thread_local.session = session
        return session

    def should_search(
        self,
        prompt: str,
        deep_search_enabled: bool = True,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[bool, str]:
        """
        Decide whether `prompt` should trigger a Wikipedia deep search and extract
        cleaned keywords. If the prompt is an image or follow-up question (e.g. 'can you show the image'
        or 'use wikipedia for image'), resolves topic from prior conversation history.
        Returns `(should_run, cleaned_query)`.
        """
        text = prompt.strip()
        if not text:
            return False, ""

        normalized = re.sub(r"[?.!,]+$", "", text).strip().lower()
        if normalized in _SKIP_PHRASES:
            return False, ""

        explicit = bool(_EXPLICIT_TRIGGER_RE.search(text))
        if not explicit:
            if not deep_search_enabled:
                return False, ""
            if _NON_WIKI_TASK_RE.search(text) or _HAS_MATH_WORDS_RE.search(text):
                return False, ""
            if not _FACTUAL_KNOWLEDGE_RE.search(text):
                return False, ""

        cleaned = _QUERY_PREFIX_RE.sub("", text).strip()
        cleaned = re.sub(r"^(?:the|a|an)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"[?.!]+$", "", cleaned).strip()

        # Check if query is generic placeholder ('image', 'pictures', 'it', 'this', 'that', empty)
        is_generic = (
            not cleaned
            or len(cleaned) < 2
            or cleaned.lower() in ("image", "images", "picture", "pictures", "photo", "photos", "it", "that", "this", "them", "info", "information")
        )

        if is_generic and history:
            # Walk backwards through conversation history to resolve original subject
            for msg in reversed(history):
                if msg.get("role") == "user":
                    candidate_text = msg.get("content", "").strip()
                    cand_cleaned = _QUERY_PREFIX_RE.sub("", candidate_text).strip()
                    cand_cleaned = re.sub(r"\s+in\s+one\s+sentence.*$", "", cand_cleaned, flags=re.IGNORECASE).strip()
                    cand_cleaned = re.sub(r"\s+briefly.*$", "", cand_cleaned, flags=re.IGNORECASE).strip()
                    cand_cleaned = re.sub(r"^(?:the|a|an)\s+", "", cand_cleaned, flags=re.IGNORECASE).strip()
                    cand_cleaned = re.sub(r"[?.!]+$", "", cand_cleaned).strip()
                    if len(cand_cleaned) >= 2 and cand_cleaned.lower() not in ("image", "images", "picture", "pictures", "it", "that", "this"):
                        cleaned = cand_cleaned
                        break

        if len(cleaned) < 2:
            cleaned = re.sub(r"[?.!]+$", "", text).strip()

        if _MATH_ONLY_RE.match(cleaned) or len(cleaned) < 2:
            return False, ""

        return True, cleaned

    def _search_titles(self, query: str, limit: int) -> List[str]:
        """Find top matching Wikipedia article titles for query."""
        session = self._get_session()
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "srprop": "snippet",
            "format": "json",
        }
        res = session.get(WIKI_API_URL, params=params, timeout=self.timeout)
        res.raise_for_status()
        hits = res.json().get("query", {}).get("search", [])
        return [item["title"] for item in hits if item.get("title")]

    def _fetch_articles_and_pageimages(self, titles: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """Batch fetch extracts, canonical URLs, and thumbnails for multiple titles."""
        if not titles:
            return [], []

        session = self._get_session()
        params = {
            "action": "query",
            "titles": "|".join(titles),
            "prop": "extracts|pageimages|info",
            "exintro": True,
            "explaintext": True,
            "exsentences": 4,
            "piprop": "thumbnail|original",
            "pithumbsize": 640,
            "inprop": "url",
            "redirects": 1,
            "format": "json",
        }
        res = session.get(WIKI_API_URL, params=params, timeout=self.timeout)
        res.raise_for_status()
        pages_dict = res.json().get("query", {}).get("pages", {})

        # Preserve search relevance ranking by matching title order
        by_title = {}
        for page in pages_dict.values():
            if page.get("missing") is not None:
                continue
            title = page.get("title", "")
            if title:
                by_title[title] = page

        ordered_pages = []
        for t in titles:
            if t in by_title:
                ordered_pages.append(by_title.pop(t))
        ordered_pages.extend(by_title.values())

        articles: List[Dict] = []
        images: List[Dict] = []

        for page in ordered_pages:
            title = page.get("title", "").strip()
            extract = page.get("extract", "").strip()
            url = page.get("fullurl") or f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"

            if extract:
                articles.append({"title": title, "url": url, "extract": extract})

            thumb = _normalize_url(page.get("thumbnail", {}).get("source", ""))
            orig = _normalize_url(page.get("original", {}).get("source", "")) or thumb
            if thumb and _is_valid_gallery_image(thumb):
                images.append(
                    {
                        "url": thumb,
                        "original_url": orig,
                        "title": title,
                        "caption": title,
                    }
                )

        return articles, images

    def _fetch_media_gallery(self, top_title: str, limit: int) -> List[Dict]:
        """Fetch rich gallery images and captions from Wikimedia REST media-list API."""
        if not top_title:
            return []

        session = self._get_session()
        encoded = quote(top_title.replace(" ", "_"), safe="")
        url = f"{WIKI_REST_MEDIA_URL}/{encoded}"
        try:
            res = session.get(url, timeout=self.timeout)
            if res.status_code != 200:
                return []
            items = res.json().get("items", [])
        except Exception as e:
            logger.debug(f"Wikipedia media-list fetch failed for '{top_title}': {e}")
            return []

        gallery: List[Dict] = []
        for item in items:
            if item.get("type") != "image":
                continue

            file_title = item.get("title", "")
            if not _is_valid_gallery_image(file_title):
                continue

            srcset = item.get("srcset") or []
            if not srcset:
                continue

            thumb_url = _normalize_url(srcset[0].get("src", ""))
            orig_url = _normalize_url(srcset[-1].get("src", "")) or thumb_url
            if not thumb_url or not _is_valid_gallery_image(thumb_url):
                continue

            caption_obj = item.get("caption") or {}
            caption = caption_obj.get("text", "").strip()
            if not caption:
                caption = file_title.replace("File:", "").rsplit(".", 1)[0].replace("_", " ")

            gallery.append(
                {
                    "url": thumb_url,
                    "original_url": orig_url,
                    "title": top_title,
                    "caption": caption[:140],
                }
            )
            if len(gallery) >= limit:
                break

        return gallery

    def deep_search(
        self,
        query: str,
        max_articles: Optional[int] = None,
        max_images: Optional[int] = None,
    ) -> Optional[Dict]:
        """
        Execute multi-article Wikipedia search + image discovery.
        Returns None gracefully if offline, timed out, or no articles match.
        """
        clean_query = query.strip()
        if not clean_query:
            return None

        art_limit = max_articles or self.max_articles
        img_limit = max_images or self.max_images

        try:
            titles = self._search_titles(clean_query, limit=art_limit)
            if not titles:
                return None

            top_title = titles[0]
            with ThreadPoolExecutor(max_workers=2) as pool:
                art_future = pool.submit(self._fetch_articles_and_pageimages, titles)
                media_future = pool.submit(self._fetch_media_gallery, top_title, img_limit)
                articles, page_images = art_future.result()
                gallery_images = media_future.result()

            if not articles and not page_images and not gallery_images:
                return None

            # Merge & deduplicate images: prioritize primary topic hero + gallery first, then related articles
            seen_urls = set()
            merged_images: List[Dict] = []

            def _add_image(img: Dict) -> None:
                if len(merged_images) >= img_limit:
                    return
                raw_url = img.get("url", "")
                if not raw_url:
                    return
                filename_key = raw_url.split("?")[0].rsplit("/", 1)[-1].lower()
                filename_key = re.sub(r"^\d+px-", "", filename_key)
                if filename_key in seen_urls:
                    return
                seen_urls.add(filename_key)
                merged_images.append(img)

            # 1. Primary article hero thumbnail
            for img in page_images[:1]:
                _add_image(img)
            # 2. Primary article gallery images with captions
            for img in gallery_images:
                _add_image(img)
            # 3. Related deep-search articles' thumbnails to fill remaining slots
            for img in page_images[1:]:
                _add_image(img)

            return {
                "query": clean_query,
                "articles": articles[:art_limit],
                "images": merged_images[:img_limit],
            }
        except Exception as e:
            logger.warning(f"Wikipedia deep search failed gracefully for '{clean_query}': {e}")
            return None

    def format_context_for_llm(self, wiki_result: Dict, max_chars: int = 1400) -> str:
        """Format Wikipedia extracts into a compact, prompt-injection guarded grounding block for Ollama."""
        if not wiki_result or not wiki_result.get("articles"):
            return ""

        lines = [f"[Wikipedia Deep Search Context for '{wiki_result.get('query', '')}']"]
        used_chars = len(lines[0])
        for idx, art in enumerate(wiki_result["articles"], start=1):
            snippet = f"{idx}. {art['title']}: {art['extract']}"
            if used_chars + len(snippet) > max_chars:
                remaining = max(120, max_chars - used_chars)
                snippet = snippet[:remaining].rsplit(" ", 1)[0] + "..."
                lines.append(snippet)
                break
            lines.append(snippet)
            used_chars += len(snippet)

        raw_context = "\n".join(lines)
        # Apply Zero-Trust Cognitive Provenance Isolation
        return prompt_guard.wrap_untrusted_content(raw_context, source_label="wikipedia")

    def fetch_image(self, image_url: str) -> Optional[Tuple[bytes, str]]:
        """
        Safely fetch an allowlisted Wikimedia/Wikipedia image with Wikimedia-compliant User-Agent.
        Enforces SSRF prevention against private IP ranges and loopbacks.
        """
        # Validate URL and enforce SSRF defense
        is_safe, reason = network_guard.validate_external_fetch(image_url)
        if not is_safe:
            logger.warning(f"Network Guard blocked image proxy request '{image_url}': {reason}")
            return None

        try:
            parsed = urlparse(image_url)
            host = (parsed.hostname or "").lower()
            if parsed.scheme != "https" or not (
                host.endswith(".wikimedia.org") or host.endswith(".wikipedia.org")
            ):
                return None

            res = self._get_session().get(image_url, timeout=self.timeout)
            if res.status_code != 200:
                return None

            content_type = res.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            if not content_type.startswith("image/"):
                return None

            return res.content, content_type
        except Exception as e:
            logger.debug(f"Failed to proxy Wikimedia image '{image_url}': {e}")
            return None
