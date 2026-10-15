from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers import auth, menu, orders, tables

app = FastAPI(title="Restaurant API")

app.include_router(auth.router)
app.include_router(menu.router)
app.include_router(tables.router)
app.include_router(orders.router)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/docs")

@app.get("/health")
async def health():
    return {"status": "ok"}