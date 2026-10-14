from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_role
from app.models import Category, MenuItem, UserRole
from app.schemas.menu import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    CategoryWithItems,
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
)

router = APIRouter(prefix="/menu", tags=["menu"])

# менять меню могут только админ и менеджер
staff_only = require_role(UserRole.admin, UserRole.manager)


@router.get("", response_model=list[CategoryWithItems])
async def get_menu(db: AsyncSession = Depends(get_db)):
    """Публичное меню: активные категории и только доступные блюда."""
    query = (
        select(Category)
        .where(Category.is_active)
        .options(selectinload(Category.items.and_(MenuItem.is_available)))

        .order_by(Category.sort_order, Category.name)
    )
    result = await db.scalars(query)
    return result.all()


@router.post("/categories", response_model=CategoryOut, status_code=201,
             dependencies=[Depends(staff_only)])
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    category = Category(**data.model_dump())
    db.add(category)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Категория с таким названием уже есть")

    await db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=CategoryOut,
              dependencies=[Depends(staff_only)])
async def update_category(
    category_id: int, data: CategoryUpdate, db: AsyncSession = Depends(get_db)
):
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    # меняем только те поля, которые клиент реально прислал

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Категория с таким названием уже есть")

    await db.refresh(category)
    return category


@router.post("/items", response_model=MenuItemOut, status_code=201,
             dependencies=[Depends(staff_only)])
async def create_item(data: MenuItemCreate, db: AsyncSession = Depends(get_db)):
    if await db.get(Category, data.category_id) is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    item = MenuItem(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/items/{item_id}", response_model=MenuItemOut,
              dependencies=[Depends(staff_only)])
async def update_item(
    item_id: int, data: MenuItemUpdate, db: AsyncSession = Depends(get_db)
):
    item = await db.get(MenuItem, item_id)

    if item is None:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")

    changes = data.model_dump(exclude_unset=True)

    new_category_id = changes.get("category_id")
    if new_category_id is not None and await db.get(Category, new_category_id) is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    for field, value in changes.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return item