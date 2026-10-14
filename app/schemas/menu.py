from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    sort_order: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class MenuItemCreate(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)



class MenuItemUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    is_available: bool | None = None


class MenuItemOut(BaseModel):
    id: int
    category_id: int
    name: str
    description: str | None
    price: Decimal
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


class CategoryWithItems(CategoryOut):
    items: list[MenuItemOut]