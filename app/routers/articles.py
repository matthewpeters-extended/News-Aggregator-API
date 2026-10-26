from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Article, Category, Source
from app.schemas import ArticleOut, PaginatedArticles

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=PaginatedArticles)
def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, description="Keyword match against title/description"),
    category: str | None = Query(None, description="Category slug"),
    source: str | None = Query(None, description="Source slug"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Article)

    if q:
        query = query.filter(
            (Article.title.ilike(f"%{q}%")) | (Article.description.ilike(f"%{q}%"))
        )
    if category:
        query = query.join(Category).filter(Category.slug == category)
    if source:
        query = query.join(Source).filter(Source.slug == source)
    if date_from:
        query = query.filter(Article.published_at >= date_from)
    if date_to:
        query = query.filter(Article.published_at <= date_to)

    total = query.count()
    items = (
        query.order_by(Article.published_at.desc()).offset(skip).limit(limit).all()
    )
    return PaginatedArticles(total=total, skip=skip, limit=limit, items=items)


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    return article
