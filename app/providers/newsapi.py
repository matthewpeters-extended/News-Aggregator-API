import json
from datetime import datetime
from pathlib import Path

import httpx

from app.config import settings
from app.providers.base import NewsProvider, NormalizedArticle

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "newsapi.json"


class NewsApiProvider(NewsProvider):
    """https://newsapi.org/v2 — aggregates many publishers under one feed,
    so each article carries its own `source.name`."""

    name = "newsapi"

    def fetch(self, query: str | None = None, category: str | None = None) -> list[NormalizedArticle]:
        if settings.app_mode == "live":
            # The real endpoints already filter server-side via `q`/`category`.
            return self._parse(self._fetch_live(query, category))

        # The mock fixture has no server to filter it, so the same filters
        # are applied client-side here instead.
        return [
            a
            for a in self._parse(self._fetch_mock())
            if (not query or query.lower() in (a.title + (a.description or "")).lower())
            and (not category or (a.category_name or "").lower() == category.lower())
        ]

    def _fetch_mock(self) -> dict:
        return json.loads(FIXTURE_PATH.read_text())

    def _fetch_live(self, query: str | None, category: str | None) -> dict:
        if not settings.newsapi_key:
            raise RuntimeError("NEWSAPI_KEY is not set")

        # NewsAPI splits keyword search and category browsing across two
        # endpoints; /top-headlines supports `category`, /everything supports
        # free-text `q`. We prefer top-headlines when a category is given.
        if category:
            url = "https://newsapi.org/v2/top-headlines"
            params = {"category": category, "language": "en", "apiKey": settings.newsapi_key}
        else:
            url = "https://newsapi.org/v2/everything"
            params = {"q": query or "news", "language": "en", "apiKey": settings.newsapi_key}

        response = httpx.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    def _parse(self, payload: dict) -> list[NormalizedArticle]:
        articles = []
        for raw in payload.get("articles", []):
            # The mock fixture tags each article with a "category" field for
            # filtering convenience; NewsAPI's real payload has no such field
            # (category is a request param, not a response field), so this
            # key is simply absent once live mode is wired up.
            article_category = raw.get("category")

            articles.append(
                NormalizedArticle(
                    external_id=raw["url"],
                    title=raw["title"],
                    description=raw.get("description"),
                    content=raw.get("content"),
                    url=raw["url"],
                    image_url=raw.get("urlToImage"),
                    published_at=datetime.fromisoformat(raw["publishedAt"].replace("Z", "+00:00")).replace(tzinfo=None),
                    source_name=raw["source"]["name"],
                    category_name=article_category,
                    author_name=raw.get("author"),
                )
            )
        return articles
