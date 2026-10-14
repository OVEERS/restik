from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserRole
from app.security import read_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = read_token(token)
    user = await db.get(User, user_id) if user_id is not None else None

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Не удалось проверить токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*roles: UserRole):
    """Использование: Depends(require_role(UserRole.admin, UserRole.manager))"""

    async def check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:

            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return user

    return check