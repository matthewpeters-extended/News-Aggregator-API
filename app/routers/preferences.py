from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Author, Category, Source, User
from app.schemas import PreferencesOut, PreferencesUpdate

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=PreferencesOut)
def get_preferences(current_user: User = Depends(get_current_user)):
    return PreferencesOut(
        sources=current_user.preferred_sources,
        categories=current_user.preferred_categories,
        authors=current_user.preferred_authors,
    )


@router.put("", response_model=PreferencesOut)
def update_preferences(
    payload: PreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.source_ids is not None:
        sources = db.query(Source).filter(Source.id.in_(payload.source_ids)).all()
        if len(sources) != len(set(payload.source_ids)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "One or more source_ids do not exist")
        current_user.preferred_sources = sources

    if payload.category_ids is not None:
        categories = db.query(Category).filter(Category.id.in_(payload.category_ids)).all()
        if len(categories) != len(set(payload.category_ids)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "One or more category_ids do not exist")
        current_user.preferred_categories = categories

    if payload.author_ids is not None:
        authors = db.query(Author).filter(Author.id.in_(payload.author_ids)).all()
        if len(authors) != len(set(payload.author_ids)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "One or more author_ids do not exist")
        current_user.preferred_authors = authors

    db.commit()
    return PreferencesOut(
        sources=current_user.preferred_sources,
        categories=current_user.preferred_categories,
        authors=current_user.preferred_authors,
    )
