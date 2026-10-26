from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base

# --- Preference many-to-many association tables ------------------------

user_preferred_sources = Table(
    "user_preferred_sources",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("source_id", Integer, ForeignKey("sources.id"), primary_key=True),
)

user_preferred_categories = Table(
    "user_preferred_categories",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True),
)

user_preferred_authors = Table(
    "user_preferred_authors",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("author_id", Integer, ForeignKey("authors.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    api_tokens = relationship(
        "ApiToken", back_populates="user", cascade="all, delete-orphan"
    )
    password_resets = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )

    preferred_sources = relationship("Source", secondary=user_preferred_sources)
    preferred_categories = relationship("Category", secondary=user_preferred_categories)
    preferred_authors = relationship("Author", secondary=user_preferred_authors)


class Source(Base):
    """A publisher, e.g. 'The Guardian' or 'TechCrunch'. Several sources can
    come from the same provider feed (NewsAPI aggregates many publishers)."""

    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    provider = Column(String, nullable=False)  # which fetch provider this came from

    articles = relationship("Article", back_populates="source")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)

    articles = relationship("Article", back_populates="category")


class Author(Base):
    """News byline, not a full profile. Deliberately thin: external feeds
    only ever give us a name string."""

    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)

    articles = relationship("Article", back_populates="author")


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_source_external_id"),)

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    url = Column(String, nullable=False, unique=True)
    image_url = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=False, index=True)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=True)

    source = relationship("Source", back_populates="articles")
    category = relationship("Category", back_populates="articles")
    author = relationship("Author", back_populates="articles")


class ApiToken(Base):
    """A long-lived personal access token for programmatic API access,
    separate from the short-lived JWT issued at /login."""

    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="api_tokens")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="password_resets")
