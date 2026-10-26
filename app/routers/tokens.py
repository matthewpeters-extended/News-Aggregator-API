from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import ApiToken, User
from app.schemas import ApiTokenCreate, ApiTokenCreated, ApiTokenOut
from app.security import generate_raw_token, hash_token

router = APIRouter(prefix="/tokens", tags=["api tokens"])


@router.post("", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
def create_token(
    payload: ApiTokenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raw_token = generate_raw_token()
    token = ApiToken(user_id=current_user.id, name=payload.name, token_hash=hash_token(raw_token))
    db.add(token)
    db.commit()
    db.refresh(token)

    return ApiTokenCreated(
        id=token.id,
        name=token.name,
        created_at=token.created_at,
        last_used_at=token.last_used_at,
        token=raw_token,
    )


@router.get("", response_model=list[ApiTokenOut])
def list_tokens(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return (
        db.query(ApiToken)
        .filter(ApiToken.user_id == current_user.id, ApiToken.revoked_at.is_(None))
        .all()
    )


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(
    token_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token = (
        db.query(ApiToken)
        .filter(ApiToken.id == token_id, ApiToken.user_id == current_user.id)
        .first()
    )
    if token is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Token not found")

    token.revoked_at = datetime.utcnow()
    db.commit()
