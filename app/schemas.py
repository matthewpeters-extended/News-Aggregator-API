from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


# --- Auth ----------------------------------------------------------------


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetRequestOut(BaseModel):
    """In mock mode there's no mail server (that's Task 3), so the raw reset
    token is handed back directly instead of emailed. A real deployment
    would email this link and return 202 with no body."""

    detail: str
    reset_token: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


# --- API tokens ------------------------------------------------------------


class ApiTokenCreate(BaseModel):
    name: str


class ApiTokenOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    last_used_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ApiTokenCreated(ApiTokenOut):
    """Returned only once, at creation time. The raw token is never stored
    or retrievable again, matching Sanctum/PAT-style tokens."""

    token: str


# --- Catalog (sources / categories / authors) -----------------------------


class SourceOut(BaseModel):
    id: int
    name: str
    slug: str
    provider: str

    model_config = ConfigDict(from_attributes=True)


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class AuthorOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


# --- Articles --------------------------------------------------------------


class ArticleOut(BaseModel):
    id: int
    title: str
    description: str | None
    content: str | None
    url: str
    image_url: str | None
    published_at: datetime
    source: SourceOut
    category: CategoryOut | None
    author: AuthorOut | None

    model_config = ConfigDict(from_attributes=True)


class PaginatedArticles(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[ArticleOut]


# --- Preferences ------------------------------------------------------------


class PreferencesUpdate(BaseModel):
    source_ids: list[int] | None = None
    category_ids: list[int] | None = None
    author_ids: list[int] | None = None


class PreferencesOut(BaseModel):
    sources: list[SourceOut]
    categories: list[CategoryOut]
    authors: list[AuthorOut]


# --- Aggregation ------------------------------------------------------------


class AggregationResult(BaseModel):
    provider: str
    fetched: int
    created: int
    skipped_duplicates: int
    error: str | None = None


class AggregationRunOut(BaseModel):
    mode: str
    results: list[AggregationResult]
