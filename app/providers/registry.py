from app.providers.base import NewsProvider
from app.providers.guardian import GuardianProvider
from app.providers.newsapi import NewsApiProvider
from app.providers.nytimes import NyTimesProvider


def get_providers() -> list[NewsProvider]:
    return [NewsApiProvider(), GuardianProvider(), NyTimesProvider()]
