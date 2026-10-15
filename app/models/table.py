from sqlalchemy import CheckConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"
    __table_args__ = (
        CheckConstraint("seats > 0", name="seats_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(unique=True)
    seats: Mapped[int] = mapped_column(default=4, server_default="4")
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())