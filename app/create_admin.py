import asyncio
from getpass import getpass

from sqlalchemy import or_, select

from app.database import SessionLocal, engine
from app.models import User, UserRole
from app.security import hash_password


async def create_admin():
    username = input("Username: ").strip()
    email = input("Email: ").strip().lower()
    password = getpass("Пароль (минимум 8 символов): ")

    if len(password) < 8:
        print("Пароль слишком короткий")
        return

    async with SessionLocal() as db:
        query = select(User).where(or_(User.username == username, User.email == email))
        if await db.scalar(query):
            print("Пользователь с таким username или email уже есть")
            return

        admin = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.admin,
        )
        db.add(admin)

        await db.commit()

    print(f"Админ {username} создан")


async def main():
    try:
        await create_admin()
    finally:
        # закрываем соединения в том же цикле событий, где они открывались
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())