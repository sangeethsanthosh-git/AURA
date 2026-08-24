"""Bounded source-aware web intelligence for AURA."""

from backend.web.manager import WebIntelligenceManager
from backend.web.models import RetrievedPage, SearchResult, WebSource

__all__ = ["RetrievedPage", "SearchResult", "WebIntelligenceManager", "WebSource"]
