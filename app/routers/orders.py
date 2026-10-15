from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import MenuItem, Order, OrderItem, OrderStatus, RestaurantTable, User, UserRole
from app.models.order import ALLOWED_TRANSITIONS
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


async def load_order(db: AsyncSession, order_id: int, lock: bool = False) -> Order | None:
    """Достаёт заказ вместе с позициями. С lock=True блокирует строку до конца транзакции."""
    query = (
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
        .execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    return await db.scalar(query)


def is_visible_to(order: Order, user: User) -> bool:
    """Клиент видит только свои заказы, сотрудники видят все."""
    return user.role != UserRole.customer or order.user_id == user.id



@router.post("", response_model=OrderOut, status_code=201)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Склеиваем одинаковые блюда: два раза "борщ" в списке это борщ x2
    quantities: dict[int, int] = {}
    for line in data.items:
        quantities[line.menu_item_id] = quantities.get(line.menu_item_id, 0) + line.quantity

    if data.table_id is not None:
        table = await db.get(RestaurantTable, data.table_id)
        if table is None or not table.is_active:
            raise HTTPException(status_code=404, detail="Столик не найден")

    # Все блюда одним запросом. Цены берём из базы, а не от клиента
    result = await db.scalars(select(MenuItem).where(MenuItem.id.in_(list(quantities))))
    menu_items = {item.id: item for item in result}

    unavailable = [
        item_id for item_id in quantities
        if item_id not in menu_items or not menu_items[item_id].is_available
    ]
    if unavailable:
        raise HTTPException(
            status_code=400,
            detail=f"Блюда не найдены или сейчас недоступны: {unavailable}",
        )


    items = []
    total = Decimal("0")
    for item_id, quantity in quantities.items():
        menu_item = menu_items[item_id]
        items.append(OrderItem(
            menu_item_id=item_id,
            name=menu_item.name,
            unit_price=menu_item.price,
            quantity=quantity,
        ))
        total += menu_item.price * quantity

    order = Order(
        user_id=user.id,
        table_id=data.table_id,
        comment=data.comment,
        total=total,
        items=items,
    )
    db.add(order)
    await db.commit()  # заказ и все его позиции сохраняются одной транзакцией

    return await load_order(db, order.id)


@router.get("", response_model=list[OrderOut])
async def list_orders(
    status: OrderStatus | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),

):
    query = select(Order).options(selectinload(Order.items))

    if user.role == UserRole.customer:
        query = query.where(Order.user_id == user.id)
    if status is not None:
        query = query.where(Order.status == status)

    query = query.order_by(Order.id.desc()).limit(limit).offset(offset)
    result = await db.scalars(query)
    return result.all()


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = await load_order(db, order_id)
    # чужой заказ отвечает 404, а не 403: не подсказываем, что такой номер существует
    if order is None or not is_visible_to(order, user):
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
async def change_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),

):
    # lock=True: пока мы меняем статус, второй запрос к этому же заказу подождёт
    order = await load_order(db, order_id, lock=True)
    if order is None or not is_visible_to(order, user):
        raise HTTPException(status_code=404, detail="Заказ не найден")

    new_status = data.status

    if user.role == UserRole.customer:
        # клиент может только отменить свой заказ, пока его не начали готовить
        if new_status != OrderStatus.cancelled or order.status != OrderStatus.new:
            raise HTTPException(
                status_code=403,
                detail="Клиент может только отменить заказ, который ещё не начали готовить",
            )

    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя перевести заказ из «{order.status.value}» в «{new_status.value}»",
        )

    order.status = new_status
    await db.commit()

    return await load_order(db, order_id)