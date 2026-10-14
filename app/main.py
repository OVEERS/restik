from fastapi import FastAPI

from app.routers import auth, menu

app = FastAPI(title="Restaurant API")

app.include_router(auth.router)
app.include_router(menu.router)


@app.get("/health")
async def health():
    return {"status": "ok"}