from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models import RestaurantTable, UserRole
from app.schemas.table import TableCreate, TableOut, TableUpdate

router = APIRouter(prefix="/tables", tags=["tables"])

staff_only = require_role(UserRole.admin, UserRole.manager)
hall_staff = require_role(UserRole.admin, UserRole.manager, UserRole.waiter)


@router.get("", response_model=list[TableOut], dependencies=[Depends(hall_staff)])
async def list_tables(db: AsyncSession = Depends(get_db)):
    result = await db.scalars(select(RestaurantTable).order_by(RestaurantTable.number))
    return result.all()


@router.post("", response_model=TableOut, status_code=201,
             dependencies=[Depends(staff_only)])
async def create_table(data: TableCreate, db: AsyncSession = Depends(get_db)):
    table = RestaurantTable(**data.model_dump())
    db.add(table)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()

        raise HTTPException(status_code=409, detail="Столик с таким номером уже есть")

    await db.refresh(table)
    return table


@router.patch("/{table_id}", response_model=TableOut, dependencies=[Depends(staff_only)])
async def update_table(
    table_id: int, data: TableUpdate, db: AsyncSession = Depends(get_db)
):
    table = await db.get(RestaurantTable, table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="Столик не найден")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(table, field, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Столик с таким номером уже есть")

    await db.refresh(table)
    return table