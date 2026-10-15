from pydantic import BaseModel, ConfigDict, Field


class TableCreate(BaseModel):
    number: int = Field(ge=1)
    seats: int = Field(default=4, ge=1, le=50)


class TableUpdate(BaseModel):
    number: int | None = Field(default=None, ge=1)
    seats: int | None = Field(default=None, ge=1, le=50)
    is_active: bool | None = None


class TableOut(BaseModel):
    id: int
    number: int
    seats: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)