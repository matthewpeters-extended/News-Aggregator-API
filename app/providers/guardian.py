import json
from datetime import datetime
from pathlib import Path

import httpx

from app.config import settings
from app.providers.base import NewsProvider, NormalizedArticle

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "guardian.json"


class GuardianProvider(NewsProvider):
    """https://open-platform.theguardian.com — single-publisher feed; every
    article's source is just "The Guardian"."""

    name = "guardian"

    def fetch(self, query: str | None = None, category: str | None = None) -> list[NormalizedArticle]:
        if settings.app_mode == "live":
            payload = self._fetch_live(query, category)
            return self._parse(payload)

        # The real Guardian API filters server-side via the `q`/`section`
        # params above; the mock fixture has no server to filter it, so we
        # apply the same filters client-side here instead.
        payload = self._fetch_mock()
        return [
            a
            for a in self._parse(payload)
            if (not query or query.lower() in (a.title + (a.description or "")).lower())
            and (not category or (a.category_name or "").lower() == category.lower())
        ]

    def _fetch_mock(self) -> dict:
        return json.loads(FIXTURE_PATH.read_text())

    def _fetch_live(self, query: str | None, category: str | None) -> dict:
        if not settings.guardian_key:
            raise RuntimeError("GUARDIAN_KEY is not set")

        params = {
            "api-key": settings.guardian_key,
            "show-fields": "trailText,body,thumbnail,byline",
        }
        if query:
            params["q"] = query
        if category:
            params["section"] = category

        response = httpx.get(
            "https://content.guardianapis.com/search", params=params, timeout=10
        )
        response.raise_for_status()
        return response.json()

    def _parse(self, payload: dict) -> list[NormalizedArticle]:
        articles = []
        for raw in payload.get("response", {}).get("results", []):
            fields = raw.get("fields", {})
            articles.append(
                NormalizedArticle(
                    external_id=raw["id"],
                    title=raw["webTitle"],
                    description=fields.get("trailText"),
                    content=fields.get("body"),
                    url=raw["webUrl"],
                    image_url=fields.get("thumbnail"),
                    published_at=datetime.fromisoformat(
                        raw["webPublicationDate"].replace("Z", "+00:00")
                    ).replace(tzinfo=None),
                    source_name="The Guardian",
                    category_name=raw.get("sectionName"),
                    author_name=fields.get("byline"),
                )
            )
        return articles
