from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.database import engine

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app = FastAPI(title="CargoLink API", version="0.2.0")


@app.get("/health")
async def health():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "service": "CargoLink API", "database": "ok"}


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
