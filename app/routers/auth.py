from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import PasswordResetToken, User
from app.schemas import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequestOut,
    RegisterRequest,
    Token,
    UserOut,
)
from app.security import (
    create_access_token,
    generate_raw_token,
    hash_password,
    hash_token,
    verify_password,
)

router = APIRouter(tags=["auth"])

RESET_TOKEN_EXPIRE_MINUTES = 30


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = User(name=payload.name, email=payload.email, password=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "email already registered")
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()

    if user is None or not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)


@router.post("/password-reset/request", response_model=PasswordResetRequestOut)
@limiter.limit("5/minute")
def request_password_reset(
    request: Request, payload: PasswordResetRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        # Don't reveal whether the email is registered.
        return PasswordResetRequestOut(detail="If that email exists, a reset token was issued", reset_token="")

    raw_token = generate_raw_token()
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
    )
    db.add(reset)
    db.commit()

    return PasswordResetRequestOut(
        detail="If that email exists, a reset token was issued", reset_token=raw_token
    )


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    reset = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hash_token(payload.token))
        .first()
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if reset is None or reset.used_at is not None or reset.expires_at < now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")

    user = db.get(User, reset.user_id)
    user.password = hash_password(payload.new_password)
    reset.used_at = now
    db.commit()
