from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
	return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
	return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
	expires_delta = timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
	expire = datetime.now(timezone.utc) + expires_delta
	to_encode = {"sub": subject, "exp": expire}
	return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> Optional[str]:
	try:
		payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
		subject: str = payload.get("sub")
		return subject
	except JWTError:
		return None