"""News headline service with NewsAPI support and RSS fallback."""

from __future__ import annotations

import html
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from backend.config.config import settings
from backend.utils.responses import error_response, success_response


@dataclass(frozen=True)
class NewsFeed:
    name: str
    url: str
    category: str


class NewsService:
    """Loads current headlines from NewsAPI, then public RSS if needed."""

    FEEDS = (
        NewsFeed("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "World"),
        NewsFeed("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml", "Technology"),
        NewsFeed("NPR News", "https://feeds.npr.org/1001/rss.xml", "General"),
        NewsFeed("The Guardian World", "https://www.theguardian.com/world/rss", "World"),
        NewsFeed("The Guardian Technology", "https://www.theguardian.com/technology/rss", "Technology"),
    )

    GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    NEWSAPI_TOP_HEADLINES = "https://newsapi.org/v2/top-headlines"
    NEWSAPI_EVERYTHING = "https://newsapi.org/v2/everything"
    NEWSAPI_CATEGORIES = {
        "business",
        "entertainment",
        "general",
        "health",
        "science",
        "sports",
        "technology",
    }

    def __init__(self, timeout: int | None = None) -> None:
        self.timeout = timeout or settings.request_timeout

    def headlines(self, category: str = "All", query: str = "", limit: int = 12) -> dict[str, Any]:
        started = time.perf_counter()
        clean_category = (category or "All").strip() or "All"
        clean_query = query.strip()
        limit = max(1, min(int(limit or 12), 24))
        try:
            articles = self._newsapi_articles(clean_category, clean_query, limit)
            source = "NewsAPI.org"
            if not articles:
                articles = self._rss_articles(clean_category, clean_query, limit)
                source = "Public RSS feeds"
            return success_response(
                "news",
                "headlines",
                {
                    "category": clean_category,
                    "query": clean_query,
                    "articles": articles,
                    "source": source,
                    "execution_time_seconds": round(time.perf_counter() - started, 3),
                },
                message=f"Loaded {len(articles)} current headlines from {source}.",
            )
        except Exception as exc:
            try:
                articles = self._rss_articles(clean_category, clean_query, limit)
                return success_response(
                    "news",
                    "headlines",
                    {
                        "category": clean_category,
                        "query": clean_query,
                        "articles": articles,
                        "source": "Public RSS feeds",
                        "execution_time_seconds": round(time.perf_counter() - started, 3),
                    },
                    message=f"NewsAPI unavailable, loaded {len(articles)} RSS headlines.",
                )
            except Exception:
                return error_response("news", "headlines", f"News headlines are unavailable: {exc}")

    def _newsapi_articles(self, category: str, query: str, limit: int) -> list[dict[str, Any]]:
        if not settings.newsapi_key:
            return []
        articles = self._fetch_newsapi(category, query, limit, country=settings.newsapi_country or "in")
        if articles or query:
            return articles
        return self._fetch_newsapi(category, query, limit, country=None)

    def _fetch_newsapi(self, category: str, query: str, limit: int, country: str | None) -> list[dict[str, Any]]:
        params = {
            "pageSize": str(limit),
            "language": "en",
        }
        clean_category = category.lower()
        if query:
            params["q"] = query
        if clean_category in self.NEWSAPI_CATEGORIES:
            params["category"] = clean_category
        if country and not query:
            params["country"] = country
        url = self.NEWSAPI_TOP_HEADLINES + "?" + "&".join(f"{key}={quote_plus(value)}" for key, value in params.items())
        request = Request(
            url,
            headers={
                "User-Agent": "AURA-MCA-MiniProject/1.0",
                "X-Api-Key": settings.newsapi_key,
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        if body.get("status") != "ok":
            raise RuntimeError(body.get("message") or "NewsAPI request failed.")
        articles = [self._newsapi_item(item, category) for item in body.get("articles", [])[:limit]]
        return [article for article in articles if article["title"]]

    def _newsapi_item(self, item: dict[str, Any], category: str) -> dict[str, Any]:
        source_name = item.get("source", {}).get("name") or "NewsAPI"
        title = str(item.get("title") or "").strip()
        description = self._clean_summary(str(item.get("description") or item.get("content") or ""))
        published = str(item.get("publishedAt") or "")
        return self._article(
            NewsFeed(source_name, "", category if category != "All" else "General"),
            title,
            str(item.get("url") or ""),
            description,
            published,
            str(item.get("urlToImage") or ""),
        )

    def _rss_articles(self, category: str, query: str, limit: int) -> list[dict[str, Any]]:
        feeds = self._feeds_for(category, query)
        articles: list[dict[str, Any]] = []
        seen: set[str] = set()
        for feed in feeds:
            for item in self._read_feed(feed):
                key = item["url"] or item["title"]
                if key in seen:
                    continue
                seen.add(key)
                articles.append(item)
                if len(articles) >= limit:
                    break
            if len(articles) >= limit:
                break
        articles.sort(key=lambda article: article.get("published_sort", 0), reverse=True)
        for article in articles:
            article.pop("published_sort", None)
        return articles[:limit]

    def _feeds_for(self, category: str, query: str) -> list[NewsFeed]:
        clean_query = query.strip()
        if clean_query:
            return [NewsFeed("Google News", self.GOOGLE_NEWS_RSS.format(query=quote_plus(clean_query)), "Search")]
        if category and category != "All":
            selected = [feed for feed in self.FEEDS if feed.category.lower() == category.lower()]
            if selected:
                return selected
        return list(self.FEEDS)

    def _read_feed(self, feed: NewsFeed) -> list[dict[str, Any]]:
        request = Request(feed.url, headers={"User-Agent": "AURA-MCA-MiniProject/1.0"})
        with urlopen(request, timeout=self.timeout) as response:
            body = response.read()
        root = ET.fromstring(body)
        channel_items = root.findall(".//item")
        atom_items = root.findall("{http://www.w3.org/2005/Atom}entry")
        if channel_items:
            return [self._rss_item(item, feed) for item in channel_items[:12]]
        return [self._atom_item(item, feed) for item in atom_items[:12]]

    def _rss_item(self, item: ET.Element, feed: NewsFeed) -> dict[str, Any]:
        title = self._text(item, "title")
        url = self._text(item, "link")
        description = self._clean_summary(self._text(item, "description"))
        published = self._text(item, "pubDate")
        image_url = self._rss_image_url(item)
        return self._article(feed, title, url, description, published, image_url)

    def _atom_item(self, item: ET.Element, feed: NewsFeed) -> dict[str, Any]:
        ns = "{http://www.w3.org/2005/Atom}"
        title = self._text(item, f"{ns}title")
        link = item.find(f"{ns}link")
        url = str(link.attrib.get("href", "")) if link is not None else ""
        description = self._clean_summary(self._text(item, f"{ns}summary") or self._text(item, f"{ns}content"))
        published = self._text(item, f"{ns}updated") or self._text(item, f"{ns}published")
        image_url = self._atom_image_url(item)
        return self._article(feed, title, url, description, published, image_url)

    def _article(self, feed: NewsFeed, title: str, url: str, description: str, published: str, image_url: str = "") -> dict[str, Any]:
        parsed = self._published_timestamp(published)
        return {
            "id": f"{feed.name}:{url or title}",
            "title": title or "Untitled headline",
            "excerpt": description or "Open the source for details.",
            "url": url,
            "source": feed.name,
            "category": feed.category,
            "published_at": published,
            "image_url": image_url,
            "published_sort": parsed,
        }

    @staticmethod
    def _rss_image_url(item: ET.Element) -> str:
        for child in item.iter():
            tag = child.tag.lower()
            if tag.endswith("thumbnail") or tag.endswith("content"):
                url = child.attrib.get("url", "")
                if url:
                    return url
            if tag.endswith("enclosure") and str(child.attrib.get("type", "")).startswith("image/"):
                return child.attrib.get("url", "")
        return ""

    @staticmethod
    def _atom_image_url(item: ET.Element) -> str:
        for child in item.iter():
            tag = child.tag.lower()
            if tag.endswith("thumbnail") or tag.endswith("content"):
                url = child.attrib.get("url", "")
                if url:
                    return url
        return ""

    @staticmethod
    def _text(item: ET.Element, tag: str) -> str:
        child = item.find(tag)
        return (child.text or "").strip() if child is not None else ""

    @staticmethod
    def _clean_summary(value: str) -> str:
        no_tags = re.sub(r"<[^>]+>", " ", value)
        return " ".join(html.unescape(no_tags).split())[:320]

    @staticmethod
    def _published_timestamp(value: str) -> float:
        if not value:
            return 0
        try:
            return parsedate_to_datetime(value).timestamp()
        except Exception:
            return 0
