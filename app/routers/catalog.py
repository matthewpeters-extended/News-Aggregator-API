from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Author, Category, Source
from app.schemas import AuthorOut, CategoryOut, SourceOut

router = APIRouter(tags=["catalog"])


@router.get("/sources", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    return db.query(Source).order_by(Source.name).all()


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


@router.get("/authors", response_model=list[AuthorOut])
def list_authors(db: Session = Depends(get_db)):
    return db.query(Author).order_by(Author.name).all()
