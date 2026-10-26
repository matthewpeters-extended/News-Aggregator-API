import re

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Article, Author, Category, Source
from app.providers.base import NewsProvider
from app.providers.registry import get_providers
from app.schemas import AggregationResult


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _get_or_create_source(db: Session, name: str, provider: str) -> Source:
    # Different feeds can capitalize the same publisher differently (e.g.
    # NewsAPI's embedded "source.name" vs a live lookup elsewhere), so dedupe
    # by slug rather than exact name — the first spelling seen wins.
    slug = slugify(name)
    source = db.query(Source).filter(Source.slug == slug).first()
    if source is not None:
        return source
    source = Source(name=name, slug=slug, provider=provider)
    db.add(source)
    db.flush()
    return source


def _get_or_create_category(db: Session, name: str | None) -> Category | None:
    if not name:
        return None
    slug = slugify(name)
    category = db.query(Category).filter(Category.slug == slug).first()
    if category is not None:
        return category
    category = Category(name=name, slug=slug)
    db.add(category)
    db.flush()
    return category


def _get_or_create_author(db: Session, name: str | None) -> Author | None:
    if not name:
        return None
    author = db.query(Author).filter(func.lower(Author.name) == name.lower()).first()
    if author is not None:
        return author
    author = Author(name=name)
    db.add(author)
    db.flush()
    return author


def run_aggregation(db: Session, providers: list[NewsProvider] | None = None) -> list[AggregationResult]:
    """Fetches from every provider and upserts normalized articles into the
    local DB. Safe to re-run: articles are keyed by (source, external_id),
    so a repeat fetch just skips what's already stored."""
    results = []

    for provider in providers or get_providers():
        try:
            normalized_articles = provider.fetch()
        except Exception as exc:  # live-mode network/credential failures
            results.append(
                AggregationResult(
                    provider=provider.name, fetched=0, created=0, skipped_duplicates=0, error=str(exc)
                )
            )
            continue

        created = 0
        skipped = 0

        for item in normalized_articles:
            source = _get_or_create_source(db, item.source_name, provider.name)

            existing = (
                db.query(Article)
                .filter(Article.source_id == source.id, Article.external_id == item.external_id)
                .first()
            )
            if existing is not None:
                skipped += 1
                continue

            category = _get_or_create_category(db, item.category_name)
            author = _get_or_create_author(db, item.author_name)

            article = Article(
                external_id=item.external_id,
                title=item.title,
                description=item.description,
                content=item.content,
                url=item.url,
                image_url=item.image_url,
                published_at=item.published_at,
                source_id=source.id,
                category_id=category.id if category else None,
                author_id=author.id if author else None,
            )
            try:
                # A SAVEPOINT so a failed insert (e.g. the same URL surfacing
                # under a different source) only unwinds this one article,
                # not the whole run's accumulated sources/categories/authors.
                with db.begin_nested():
                    db.add(article)
                    db.flush()
                created += 1
            except IntegrityError:
                skipped += 1

        results.append(
            AggregationResult(
                provider=provider.name,
                fetched=len(normalized_articles),
                created=created,
                skipped_duplicates=skipped,
            )
        )

    db.commit()
    return results
