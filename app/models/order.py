import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderStatus(str, enum.Enum):
    new = "new"
    cooking = "cooking"
    ready = "ready"
    served = "served"
    paid = "paid"
    cancelled = "cancelled"


# из какого статуса в какие можно перейти
ALLOWED_TRANSITIONS = {
    OrderStatus.new: {OrderStatus.cooking, OrderStatus.cancelled},
    OrderStatus.cooking: {OrderStatus.ready, OrderStatus.cancelled},
    OrderStatus.ready: {OrderStatus.served},
    OrderStatus.served: {OrderStatus.paid},
    OrderStatus.paid: set(),
    OrderStatus.cancelled: set(),
}


class Order(Base):
    __tablename__ = "orders"


    id: Mapped[int] = mapped_column(primary_key=True)
    # кто создал заказ: клиент или официант
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # стол может быть пустым: заказ на вынос или онлайн
    table_id: Mapped[int | None] = mapped_column(ForeignKey("restaurant_tables.id"))
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=20,
             values_callable=lambda statuses: [s.value for s in statuses]),
        default=OrderStatus.new,
        server_default=OrderStatus.new.value,
        index=True,
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    comment: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_not_negative"),

    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    # название и цену копируем на момент заказа: меню потом изменится,
    # а чек должен остаться прежним
    name: Mapped[str] = mapped_column(String(150))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quantity: Mapped[int]

    order: Mapped["Order"] = relationship(back_populates="items")