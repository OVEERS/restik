from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import settings

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def check_password(password: str, hashed: str) -> bool:
    return password_hasher.verify(password, hashed)


def make_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    data = {"sub": str(user_id), "exp": expire}
    return jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)


def read_token(token: str) -> int | None:
    """Возвращает id пользователя из токена или None, если токен плохой или просрочен."""
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return int(data["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None