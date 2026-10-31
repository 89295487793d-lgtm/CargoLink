from pathlib import Path
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from app.config import get_settings
from app.database import SessionLocal, engine
from app.models import CargoRequest, User

settings = get_settings()

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app = FastAPI(title="CargoLink API", version="0.5.0")


def request_payload(row: CargoRequest) -> dict:
    cargo = row.cargo or ""
    category = row.cargo_category or ("liquid" if any(word in cargo.lower() for word in ("дт", "дизел", "бенз", "мазут", "топлив", "нефт", "масло", "аммиак", "жидк")) else "dry")
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
        "vat_mode": row.vat_mode,
        "payment_method": row.payment_method,
        "price_terms": ("С НДС, безнал" if row.vat_mode == "С НДС" else "Без НДС, безнал" if row.vat_mode == "Без НДС" and row.payment_method == "Безналичный расчёт" else "Наличными" if row.payment_method == "Наличные" else "Запрос ставки" if row.payment_method == "Запрос ставки" else None),
        "volume_m3": row.volume_m3,
        "unloading_date": row.unloading_date,
        "adr_class": row.adr_class,
        "comment": row.comment,
        "status": row.status,
        "delivery_status": row.delivery_status,
    }



class CreateRequest(BaseModel):
    origin: str = Field(min_length=3, max_length=300)
    destination: str = Field(min_length=3, max_length=300)
    cargo: str = Field(min_length=2, max_length=300)
    category: str = Field(pattern="^(liquid|dry)$")
    weight_tons: float = Field(gt=0, le=100000)
    volume_m3: float | None = Field(default=None, gt=0, le=1000000)
    adr_class: str | None = Field(default=None, max_length=10)
    vehicle_type: str = Field(min_length=2, max_length=200)
    pickup_date: str = Field(min_length=4, max_length=100)
    unloading_date: str | None = Field(default=None, max_length=100)
    price_rub: str | None = Field(default=None, max_length=100)
    vat_mode: str | None = Field(default=None, pattern="^(С НДС|Без НДС)$")
    payment_method: str = Field(default="Безналичный расчёт", pattern="^(Безналичный расчёт|Наличные|Запрос ставки)$")
    comment: str | None = Field(default=None, max_length=1000)


def telegram_webapp_user(init_data: str) -> dict:
    if not settings.bot_token:
        raise HTTPException(status_code=503, detail="Telegram authentication is not configured")
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash")
        auth_date = int(pairs["auth_date"])
        user = json.loads(pairs["user"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Invalid Telegram initData")
    if not isinstance(user, dict) or not user.get("id"):
        raise HTTPException(status_code=401, detail="Telegram user is missing")
    if auth_date > int(time.time()) + 60 or int(time.time()) - auth_date > 86400:
        raise HTTPException(status_code=401, detail="Telegram session expired")
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=401, detail="Telegram signature check failed")
    return user


@app.post("/api/requests")
async def create_request(payload: CreateRequest, x_telegram_init_data: str = Header(default="")):
    telegram_user = telegram_webapp_user(x_telegram_init_data)
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == int(telegram_user["id"])))
        user = result.scalar_one_or_none()
        if user is None or not user.full_name:
            raise HTTPException(status_code=403, detail="Complete CargoLink registration in Telegram first")
        row = CargoRequest(
            customer_id=user.id,
            origin=payload.origin.strip(),
            destination=payload.destination.strip(),
            cargo=payload.cargo.strip(),
            cargo_category=payload.category,
            weight_tons=payload.weight_tons,
            volume_m3=payload.volume_m3,
            adr_class=payload.adr_class,
            vehicle_type=payload.vehicle_type.strip(),
            pickup_date=payload.pickup_date,
            unloading_date=payload.unloading_date,
            price_rub=payload.price_rub,
            vat_mode=payload.vat_mode,
            payment_method=payload.payment_method,
            comment=payload.comment,
            status="open",
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return {"ok": True, "item": request_payload(row)}


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
