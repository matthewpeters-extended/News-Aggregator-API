from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NormalizedArticle:
    """The shape every provider must normalize its raw response into, so the
    aggregator never needs to know which API an article came from."""

    external_id: str
    title: str
    url: str
    published_at: datetime
    source_name: str
    description: str | None = None
    content: str | None = None
    image_url: str | None = None
    category_name: str | None = None
    author_name: str | None = None


class NewsProvider(ABC):
    """One implementation per external API. `name` identifies the provider
    in aggregation results and on the Source.provider column."""

    name: str

    @abstractmethod
    def fetch(
        self,
        query: str | None = None,
        category: str | None = None,
    ) -> list[NormalizedArticle]:
        """Fetch and normalize articles, optionally filtered by a keyword
        and/or category. Filtering here mirrors what the real APIs accept
        as query params, so swapping a mock provider for a live one needs
        no changes to the aggregator."""
        raise NotImplementedError
