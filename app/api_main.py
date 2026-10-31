from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from app.database import SessionLocal, engine
from app.models import CargoRequest

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app = FastAPI(title="CargoLink API", version="0.3.0")


@app.get("/health")
async def health():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "service": "CargoLink API", "database": "ok"}


@app.get("/api/requests")
async def list_requests():
    async with SessionLocal() as session:
        result = await session.execute(
            select(CargoRequest).where(CargoRequest.status == "open").order_by(CargoRequest.created_at.desc())
        )
        rows = result.scalars().all()
        return [
            {
                "id": row.id,
                "origin": row.origin,
                "destination": row.destination,
                "cargo": row.cargo,
                "weight_tons": row.weight_tons,
                "vehicle_type": row.vehicle_type,
                "pickup_date": row.pickup_date,
                "price_rub": row.price_rub,
                "status": row.status,
            }
            for row in rows
        ]


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
