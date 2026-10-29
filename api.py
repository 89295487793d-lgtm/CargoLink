from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import logging
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import engine, SessionLocal, init_db
from app.auth import current_user
from app.models import User, Load, Offer, FreeVehicle, ServiceListing, PartnerPost, PartnerComment, UserReport

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await engine.dispose()

app = FastAPI(title="CargoLink API", version="0.1.0", lifespan=lifespan)
logging.basicConfig(level=logging.INFO)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def home():
    return FileResponse("frontend/index.html")

async def db_session():
    async with SessionLocal() as session:
        yield session

class ProfileIn(BaseModel):
    fio: str = Field(min_length=3, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    organization: str | None = Field(default=None, max_length=200)
    inn: str | None = Field(default=None, max_length=12)
    specialization: str | None = Field(default=None, max_length=120)

class LoadIn(BaseModel):
    origin_city: str = Field(min_length=2, max_length=120)
    origin_address: str | None = Field(default=None, max_length=250)
    destination_city: str = Field(min_length=2, max_length=120)
    destination_address: str | None = Field(default=None, max_length=250)
    vehicle_type: str = Field(min_length=2, max_length=100)
    cargo_type: str = Field(min_length=2, max_length=120)
    weight_tons: float | None = Field(default=None, ge=0)
    volume_m3: float | None = Field(default=None, ge=0)
    hazard_class: str = "Неопасный"
    date_text: str | None = None
    rate_mode: str = "quote"
    rate_amount: float | None = Field(default=None, ge=0)
    vat_mode: str = "no_vat"
    comment: str | None = Field(default=None, max_length=1000)

class OfferIn(BaseModel):
    amount: float = Field(gt=0)
    vat_mode: str = "no_vat"
    comment: str | None = Field(default=None, max_length=1000)

class VehicleIn(BaseModel):
    cargo_category: str
    tonnage: float = Field(gt=0)
    description: str = Field(min_length=2, max_length=1000)
    expires_at: str
    photo_url: str | None = None

class ServiceIn(BaseModel):
    category: str
    name: str = Field(min_length=2, max_length=200)
    city: str = Field(min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=250)
    details: str | None = Field(default=None, max_length=2000)
    contacts: str | None = Field(default=None, max_length=250)
    photo_url: str | None = None

class PartnerIn(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    inn: str | None = Field(default=None, max_length=12)
    description: str = Field(min_length=10, max_length=4000)
    evidence_note: str | None = Field(default=None, max_length=2000)

class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

class ReportIn(BaseModel):
    target_type: str
    target_id: int
    reason: str = Field(min_length=5, max_length=2000)

def as_dict(obj, fields):
    return {f: getattr(obj, f) for f in fields}

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "CargoLink API"}

@app.get("/api/profile")
async def get_profile(user: User = Depends(current_user)):
    return {"id": user.id, "fio": user.fio, "username": user.username, "phone_set": bool(user.phone),
            "organization": user.organization, "inn": user.inn, "specialization": user.specialization}

@app.put("/api/profile")
async def update_profile(data: ProfileIn, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    obj = await session.get(User, user.id)
    obj.fio, obj.organization, obj.inn, obj.specialization = data.fio, data.organization, data.inn, data.specialization
    # Phone remains private and can only be set via Telegram contact sharing, not arbitrary Mini App input.
    await session.commit()
    return {"ok": True, "profile": {"fio": obj.fio, "organization": obj.organization, "inn": obj.inn, "specialization": obj.specialization}}

@app.get("/api/loads")
async def list_loads(category: str = "all", q: str = "", user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    stmt = select(Load).where(Load.status == "active")
    if category == "Наливные":
        stmt = stmt.where(Load.cargo_type.in_(["Нефтепродукты", "Химическая продукция", "Жидкие грузы"]))
    elif category == "Сухие":
        stmt = stmt.where(~Load.cargo_type.in_(["Нефтепродукты", "Химическая продукция", "Жидкие грузы"]))
    if q:
        stmt = stmt.where((Load.origin_city.ilike(f"%{q}%")) | (Load.destination_city.ilike(f"%{q}%")) | (Load.cargo_type.ilike(f"%{q}%")))
    stmt = stmt.order_by(desc(Load.created_at)).limit(100)
    rows = (await session.execute(stmt)).scalars().all()
    return [as_dict(x, ["id","origin_city","origin_address","destination_city","destination_address","vehicle_type","cargo_type","weight_tons","volume_m3","hazard_class","date_text","rate_mode","rate_amount","vat_mode","comment","status"]) for x in rows]

@app.post("/api/loads")
async def create_load(data: LoadIn, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    if data.rate_mode == "fixed" and data.rate_amount is None:
        raise HTTPException(400, "Укажите фиксированную стоимость или выберите запрос ставки.")
    row = Load(owner_id=user.id, **data.model_dump())
    session.add(row); await session.commit(); await session.refresh(row)
    return {"ok": True, "id": row.id}

@app.get("/api/loads/{load_id}")
async def load_detail(load_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    row = await session.get(Load, load_id)
    if not row or row.status != "active":
        raise HTTPException(404, "Заявка не найдена или неактивна")
    return as_dict(row, ["id","owner_id","origin_city","origin_address","destination_city","destination_address","vehicle_type","cargo_type","weight_tons","volume_m3","hazard_class","date_text","rate_mode","rate_amount","vat_mode","comment","status"])

@app.post("/api/loads/{load_id}/offers")
async def create_offer(load_id: int, data: OfferIn, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    row = await session.get(Load, load_id)
    if not row or row.status != "active": raise HTTPException(404, "Активная заявка не найдена")
    if row.owner_id == user.id: raise HTTPException(400, "Нельзя предложить ставку на собственную заявку")
    offer = Offer(load_id=load_id, carrier_id=user.id, **data.model_dump())
    session.add(offer); await session.commit(); await session.refresh(offer)
    return {"ok": True, "id": offer.id}

@app.get("/api/my/loads")
async def my_loads(user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    rows = (await session.execute(select(Load).where(Load.owner_id == user.id).order_by(desc(Load.created_at)))).scalars().all()
    return [as_dict(x, ["id","origin_city","destination_city","cargo_type","vehicle_type","status","rate_mode","rate_amount","created_at"]) for x in rows]

@app.post("/api/loads/{load_id}/status")
async def update_load_status(load_id: int, status: str = Query(..., pattern="^(completed|cancelled|active)$"), user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    row = await session.get(Load, load_id)
    if not row: raise HTTPException(404, "Заявка не найдена")
    if row.owner_id != user.id: raise HTTPException(403, "Менять статус может только автор заявки")
    row.status = status
    await session.commit()
    return {"ok": True, "status": row.status}

@app.get("/api/vehicles")
async def list_vehicles(user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    rows = (await session.execute(select(FreeVehicle).where(FreeVehicle.status=="active").order_by(desc(FreeVehicle.created_at)).limit(100))).scalars().all()
    return [as_dict(x, ["id","cargo_category","tonnage","description","expires_at","photo_url"]) for x in rows]

@app.post("/api/vehicles")
async def create_vehicle(data: VehicleIn, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    row = FreeVehicle(owner_id=user.id, **data.model_dump())
    session.add(row); await session.commit(); await session.refresh(row)
    return {"ok": True, "id": row.id}

@app.get("/api/services")
async def list_services(category: str = "all", city: str = "", user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    stmt = select(ServiceListing).where(ServiceListing.status=="active")
    if category != "all": stmt = stmt.where(ServiceListing.category == category)
    if city: stmt = stmt.where(ServiceListing.city.ilike(f"%{city}%"))
    rows = (await session.execute(stmt.order_by(desc(ServiceListing.created_at)).limit(100))).scalars().all()
    return [as_dict(x, ["id","category","name","city","address","details","contacts","photo_url"]) for x in rows]

@app.post("/api/services")
async def create_service(data: ServiceIn, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    if data.category not in {"АЗС","СТО","Шиномонтаж"}: raise HTTPException(400, "Недопустимая категория")
    row = ServiceListing(owner_id=user.id, **data.model_dump())
    session.add(row); await session.commit(); await session.refresh(row)
    return {"ok": True, "id": row.id}

@app.get("/api/partners")
async def list_partners(q: str = "", user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    stmt = select(PartnerPost).where(PartnerPost.status=="published")
    if q: stmt = stmt.where((PartnerPost.organization_name.ilike(f"%{q}%")) | (PartnerPost.inn.ilike(f"%{q}%")))
    rows = (await session.execute(stmt.order_by(desc(PartnerPost.created_at)).limit(100))).scalars().all()
    return [as_dict(x, ["id","organization_name","inn","description","evidence_note","created_at"]) for x in rows]

@app.post("/api/partners")
async def create_partner(data: PartnerIn, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    row = PartnerPost(owner_id=user.id, status="pending_review", **data.model_dump())
    session.add(row); await session.commit(); await session.refresh(row)
    return {"ok": True, "id": row.id, "status": "pending_review", "notice": "Публикация ожидает модерации"}

@app.get("/api/partners/{post_id}/comments")
async def list_comments(post_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    rows = (await session.execute(select(PartnerComment).where(PartnerComment.post_id==post_id).order_by(PartnerComment.created_at))).scalars().all()
    return [as_dict(x, ["id","post_id","owner_id","body","created_at"]) for x in rows]

@app.post("/api/partners/{post_id}/comments")
async def add_comment(post_id: int, data: CommentIn, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    post = await session.get(PartnerPost, post_id)
    if not post or post.status != "published": raise HTTPException(404, "Публикация не найдена")
    row = PartnerComment(post_id=post_id, owner_id=user.id, body=data.body)
    session.add(row); await session.commit(); await session.refresh(row)
    return {"ok": True, "id": row.id}

@app.post("/api/reports")
async def create_report(data: ReportIn, user: User = Depends(current_user), session: AsyncSession = Depends(db_session)):
    row = UserReport(reporter_id=user.id, **data.model_dump())
    session.add(row); await session.commit()
    return {"ok": True, "notice": "Жалоба принята на рассмотрение"}

@app.get("/api/notifications")
async def notifications(user: User = Depends(current_user)):
    # Notification storage/Telegram delivery worker is a later integration.
    return {"items": [], "note": "Уведомления подключаются по мере реализации событий."}
