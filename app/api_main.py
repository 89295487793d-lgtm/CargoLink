from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from app.database import SessionLocal, engine
from app.models import CargoRequest

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app = FastAPI(title="CargoLink API", version="0.4.0")


def request_payload(row: CargoRequest) -> dict:
    cargo = row.cargo or ""
    category = "liquid" if any(word in cargo.lower() for word in ("дт", "дизел", "бенз", "мазут", "топлив", "нефт", "масло", "аммиак", "жидк")) else "dry"
    return {
        "id": row.id,
        "origin": row.origin,
        "destination": row.destination,
        "cargo": row.cargo,
        "category": category,
        "weight_tons": row.weight_tons,
        "vehicle_type": row.vehicle_type,
        "pickup_date": row.pickup_date,
        "price_rub": row.price_rub,
        "status": row.status,
    }


@app.get("/health")
async def health():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "service": "CargoLink API", "database": "ok"}


@app.get("/api/requests")
async def list_requests(
    category: str = Query(default="all", pattern="^(all|liquid|dry)$"),
    origin: str = "",
    destination: str = "",
    cargo: str = "",
    vehicle: str = "",
    limit: int = Query(default=50, ge=1, le=100),
):
    async with SessionLocal() as session:
        result = await session.execute(
            select(CargoRequest)
            .where(CargoRequest.status == "open")
            .order_by(CargoRequest.created_at.desc())
            .limit(500)
        )
        rows = result.scalars().all()
    items = [request_payload(row) for row in rows]
    if category != "all":
        items = [item for item in items if item["category"] == category]
    if origin:
        items = [item for item in items if origin.casefold() in item["origin"].casefold()]
    if destination:
        items = [item for item in items if destination.casefold() in item["destination"].casefold()]
    if cargo:
        items = [item for item in items if cargo.casefold() in item["cargo"].casefold()]
    if vehicle:
        items = [item for item in items if vehicle.casefold() in item["vehicle_type"].casefold()]
    return {"total": len(items), "items": items[:limit]}


@app.get("/api/requests/{request_id}")
async def get_request(request_id: int):
    async with SessionLocal() as session:
        result = await session.execute(select(CargoRequest).where(CargoRequest.id == request_id))
        row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return request_payload(row)


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
