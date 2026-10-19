from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Category, MenuItem, User, UserRole
from app.security import hash_password, make_token

PASSWORD = "password123"


async def create_user(username: str, role: UserRole = UserRole.customer) -> User:
    """Создаёт пользователя сразу в базе (админа через API не создать)."""
    async with SessionLocal() as db:
        user = User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=hash_password(PASSWORD),
            role=role,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    """Заголовок авторизации для запросов от имени пользователя."""
    return {"Authorization": f"Bearer {make_token(user.id)}"}


async def create_dish(name: str = "Борщ", price: str = "350.00", available: bool = True) -> MenuItem:

    """Создаёт блюдо в категории «Основное» (категория создаётся при первом вызове)."""
    async with SessionLocal() as db:
        category = await db.scalar(select(Category).where(Category.name == "Основное"))
        if category is None:
            category = Category(name="Основное")
            db.add(category)
            await db.flush()

        dish = MenuItem(
            category_id=category.id,
            name=name,
            price=Decimal(price),
            is_available=available,
        )
        db.add(dish)
        await db.commit()
        await db.refresh(dish)
    return dish