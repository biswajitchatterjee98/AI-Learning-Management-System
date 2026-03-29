from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.security import decode_token
from app.db import SessionLocal
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
        user_id_raw = payload.get("sub")
        tenant_id_raw = payload.get("tenant_id")
        if not user_id_raw or not tenant_id_raw:
            raise ValueError("Missing claims")
        user_id = UUID(str(user_id_raw))
        tenant_id = UUID(str(tenant_id_raw))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.scalar(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def require_roles(*allowed_roles: str):
    def _inner(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")
        return user

    return _inner

