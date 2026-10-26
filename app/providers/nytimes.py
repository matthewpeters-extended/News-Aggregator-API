import json
from datetime import datetime
from pathlib import Path

import httpx

from app.config import settings
from app.providers.base import NewsProvider, NormalizedArticle

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "nytimes.json"


class NyTimesProvider(NewsProvider):
    """https://developer.nytimes.com/docs/articlesearch-product/1/overview
    — single-publisher feed; every article's source is "The New York Times"."""

    name = "nytimes"

    def fetch(self, query: str | None = None, category: str | None = None) -> list[NormalizedArticle]:
        if settings.app_mode == "live":
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
        if not settings.nytimes_key:
            raise RuntimeError("NYTIMES_KEY is not set")

        filters = []
        if category:
            filters.append(f'section_name:("{category}")')
        fq = " AND ".join(filters) if filters else None

        params = {"api-key": settings.nytimes_key}
        if query:
            params["q"] = query
        if fq:
            params["fq"] = fq

        response = httpx.get(
            "https://api.nytimes.com/svc/search/v2/articlesearch.json",
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def _parse(self, payload: dict) -> list[NormalizedArticle]:
        articles = []
        for raw in payload.get("response", {}).get("docs", []):
            image_url = None
            for media in raw.get("multimedia", []):
                if media.get("subtype") == "thumbnail":
                    image_url = f"https://static01.nyt.com/{media['url']}"
                    break

            # NYTimes uses offset-less timestamps like "+0000"; isoformat
            # with a colon-free offset needs a small normalization step.
            pub_date = raw["pub_date"]
            if pub_date[-5] in "+-" and pub_date[-3] != ":":
                pub_date = f"{pub_date[:-2]}:{pub_date[-2:]}"

            byline = (raw.get("byline") or {}).get("original")
            author_name = byline.removeprefix("By ") if byline else None

            articles.append(
                NormalizedArticle(
                    external_id=raw["_id"],
                    title=raw["headline"]["main"],
                    description=raw.get("abstract"),
                    content=None,  # Article Search API doesn't return full body text
                    url=raw["web_url"],
                    image_url=image_url,
                    published_at=datetime.fromisoformat(pub_date).replace(tzinfo=None),
                    source_name="The New York Times",
                    category_name=raw.get("section_name"),
                    author_name=author_name,
                )
            )
        return articles
