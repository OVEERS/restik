from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.user import Token, UserCreate, UserOut
from app.security import check_password, hash_password, make_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    email = data.email.lower()

    query = select(User).where(or_(User.email == email, User.username == data.username))
    if await db.scalar(query):
        raise HTTPException(status_code=409, detail="Такой username или email уже занят")

    user = User(
        username=data.username,
        email=email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        # два человека одновременно зарегистрировались с одним email
        await db.rollback()
        raise HTTPException(status_code=409, detail="Такой username или email уже занят")

    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # В форме поле называется username, но пускаем и по email
    query = select(User).where(
        or_(User.username == form.username, User.email == form.username.lower())
    )
    user = await db.scalar(query)

    if user is None or not check_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Аккаунт отключён")

    return Token(access_token=make_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user