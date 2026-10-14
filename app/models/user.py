import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    waiter = "waiter"
    cook = "cook"
    customer = "customer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        # в БД это обычная строка, а не PG enum: так проще добавлять роли
        Enum(UserRole, native_enum=False, length=20,
             values_callable=lambda roles: [r.value for r in roles]),
        default=UserRole.customer,
        server_default=UserRole.customer.value,
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )