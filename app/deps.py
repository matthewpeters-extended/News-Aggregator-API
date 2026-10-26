from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiToken, User
from app.security import decode_access_token, hash_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Accepts either a short-lived JWT from /login or a long-lived API
    token from /tokens, both as `Authorization: Bearer <value>`."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is not None:
        user_id = payload.get("sub")
        user = db.get(User, int(user_id)) if user_id is not None else None
        if user is None:
            raise credentials_exception
        return user

    api_token = (
        db.query(ApiToken)
        .filter(ApiToken.token_hash == hash_token(token), ApiToken.revoked_at.is_(None))
        .first()
    )
    if api_token is None:
        raise credentials_exception

    api_token.last_used_at = datetime.utcnow()
    db.commit()

    user = db.get(User, api_token.user_id)
    if user is None:
        raise credentials_exception
    return user
