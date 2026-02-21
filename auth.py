"""
Authentication & Authorization — JWT-based with bcrypt password hashing.
SECRET_KEY MUST be set via the SECRET_KEY environment variable in production.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from models import Doctor, get_db

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
# IMPORTANT: set a strong SECRET_KEY environment variable before deploying.
_DEFAULT_KEY = "CHANGE-ME-use-env-SECRET_KEY-in-production-min-32-chars!!"
SECRET_KEY: str = os.environ.get("SECRET_KEY", _DEFAULT_KEY)
if SECRET_KEY == _DEFAULT_KEY:
    logger.warning(
        "SECRET_KEY is using the default insecure value. "
        "Set the SECRET_KEY environment variable before deploying to production."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "480"))  # 8 h

# ── Crypto helpers ────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security    = HTTPBearer()


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_doctor(username: str, password: str, db: Session) -> Optional[Doctor]:
    """Return the Doctor if credentials are valid, otherwise None."""
    doctor = db.query(Doctor).filter(Doctor.username == username).first()
    if doctor is None or not verify_password(password, doctor.hashed_password):
        return None
    return doctor


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Return the username (sub claim) or None if the token is invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if not isinstance(username, str) or not username:
            return None
        return username
    except JWTError:
        # Do NOT log the token itself — avoid leaking credentials
        return None


def get_current_doctor(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Doctor:
    """FastAPI dependency — validates JWT and returns the authenticated Doctor."""
    username = decode_access_token(credentials.credentials)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    doctor = db.query(Doctor).filter(Doctor.username == username).first()
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Doctor account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return doctor
