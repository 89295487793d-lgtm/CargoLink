from contextlib import asynccontextmanager
from datetime import date
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from db import Base, engine, get_db
from models import User, Load, Offer, Vehicle, ServiceListing, PartnerPost
from auth import get_telegram_user

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app=FastAPI(title="CargoLink API",version="0.1.0",lifespan=lifespan)
app.mount("/static",StaticFiles(directory="static"),name="static")
@app.get("/")
def home(): return FileResponse("static/index.html")
@app.get("/health")
def health(): return {"ok":True,"service":"CargoLink"}

class ProfileIn(BaseModel):
    fio: str=Field(min_length=3,max_length=200)
    phone: Optional[str]=None
    organization: Optional[str]=None
    inn: Optional[str]=Field(default=None,max_length=12)
    specialization: Optional[str]=None
class LoadIn(BaseModel):
    origin: str=Field(min_length=2,max_length=200)
    destination: str=Field(min_length=2,max_length=200)
    vehicle_type: str="Не указан"
    cargo_type: str="Не указан"
    weight_t: Optional[str]=None
    volume_m3: Optional[str]=None
    hazard_class: str="Неопасный"
    rate_type: str="request"
    rate_amount: Optional[str]=None
    vat: str="Не указано"
    comment: Optional[str]=Field(default=None,max_length=1000)
class OfferIn(BaseModel):
    amount: str=Field(min_length=1,max_length=30)
    vat: str="Не указано"
    comment: Optional[str]=Field(default=None,max_length=1000)
class VehicleIn(BaseModel):
    category: str
    tonnage: str
    description: str=Field(min_length=2,max_length=1000)
    expires_on: str
class ServiceIn(BaseModel):
    category: str
    city: str=Field(min_length=2,max_length=150)
    title: str=Field(min_length=2,max_length=200)
    address: Optional[str]=None
    contacts: Optional[str]=None
    description: Optional[str]=Field(default=None,max_length=1000)
class PartnerIn(BaseModel):
    company_name: str=Field(min_length=2,max_length=200)
    inn: Optional[str]=None
    description: str=Field(min_length=10,max_length=3000)
def dump(x): return {c.name:getattr(x,c.name) for c in x.__table__.columns}

@app.get("/api/profile")
def profile(uid:int=Depends(get_telegram_user),db:Session=Depends(get_db)):
    u=db.scalar(select(User).where(User.telegram_id==uid))
    if not u:return {"telegram_id":uid,"fio":"","phone":None,"organization":None,"inn":None,"specialization":None}
    d=dump(u); d["phone"]=None if u.phone_private else u.phone
    return d
@app.put("/api/profile")
def save_profile(p:ProfileIn,uid:int=Depends(get_telegram_user),db:Session=Depends(get_db)):
    u=db.scalar(select(User).where(User.telegram_id==uid))
    if not u:u=User(telegram_id=uid,fio=p.fio);db.add(u)
    for k,v in p.model_dump().items():setattr(u,k,v)
    u.phone_private=True;db.commit()
    return {"ok":True,"message":"Профиль сохранён; телефон скрыт."}

@app.get("/api/loads")
def loads(category:Optional[str]=None,q:Optional[str]=None,db:Session=Depends(get_db)):
    xs=list(db.scalars(select(Load).where(Load.status=="active").order_by(Load.id.desc()).limit(100)))
    if category:xs=[x for x in xs if category.lower() in x.cargo_type.lower()]
    if q:xs=[x for x in xs if q.lower() in (x.origin+x.destination+x.cargo_type).lower()]
    return [dump(x) for x in xs]
@app.post("/api/loads")
def create_load(p:LoadIn,uid:int=Depends(get_telegram_user),db:Session=Depends(get_db)):
    d=p.model_dump()
    if d["rate_type"] not in ("fixed","request"):raise HTTPException(400,"Некорректный тип ставки")
    if d["rate_type"]=="fixed" and not d["rate_amount"]:raise HTTPException(400,"Укажите фиксированную ставку")
    x=Load(owner_telegram_id=uid,**d);db.add(x);db.commit();db.refresh(x);return dump(x)
@app.get("/api/my/loads")
def my_loads(uid:int=Depends(get_telegram_user),db:Session=Depends(get_db)):
    return [dump(x) for x in db.scalars(select(Load).where(Load.owner_telegram_id==uid).order_by(Load.id.desc()))]
@app.patch("/api/loads/{load_id}/status")
def status(load_id:int,status:str,uid:int=Depends(get_telegram_user),db:Session=Depends(get_db)):
    if status not in ("active","completed","cancelled"):raise HTTPException(400,"Некорректный статус")
    x=db.get(Load,load_id)
    if not x:raise HTTPException(404,"Заявка не найдена")
    if x.owner_telegram_id!=uid:raise HTTPException(403,"Менять статус может только владелец")
    x.status=status;db.commit();return {"ok":True,"status":status}
@app.post("/api/loads/{load_id}/offers")
def offer(load_id:int,p:OfferIn,uid:int=Depends(get_telegram_user),db:Session=Depends(get_db)):
    x=db.get(Load,load_id)
    if not x or x.status!="active":raise HTTPException(404,"Заявка не найдена")
    if x.owner_telegram_id==uid:raise HTTPException(400,"Нельзя предложить ставку на свою заявку")
    o=Offer(load_id=load_id,carrier_telegram_id=uid,**p.model_dump());db.add(o);db.commit();db.refresh(o);return dump(o)

@app.get("/api/vehicles")
def vehicles(db:Session=Depends(get_db)):
    today=date.today().isoformat()
    return [dump(x) for x in db.scalars(select(Vehicle).where(Vehicle.status=="active").order_by(Vehicle.id.desc())) if x.expires_on>=today]
@app.post("/api/vehicles")
def create_vehicle(p:VehicleIn,uid:int=Depends(get_telegram_user),db:Session=Depends(get_db)):
    try:
        if date.fromisoformat(p.expires_on)<date.today():raise HTTPException(400,"Дата окончания в прошлом")
    except ValueError:raise HTTPException(400,"Дата должна быть ГГГГ-ММ-ДД")
    x=Vehicle(owner_telegram_id=uid,**p.model_dump());db.add(x);db.commit();db.refresh(x);return dump(x)

@app.get("/api/services")
def services(category:Optional[str]=None,city:Optional[str]=None,db:Session=Depends(get_db)):
    xs=list(db.scalars(select(ServiceListing).where(ServiceListing.status=="active").order_by(ServiceListing.id.desc()).limit(200)))
    if category:xs=[x for x in xs if x.category==category]
    if city:xs=[x for x in xs if city.lower() in x.city.lower()]
    return [dump(x) for x in xs]
@app.post("/api/services")
def create_service(p:ServiceIn,uid:int=Depends(get_telegram_user),db:Session=Depends(get_db)):
    if p.category not in ("АЗС","СТО","Шиномонтаж"):raise HTTPException(400,"Категория: АЗС, СТО или Шиномонтаж")
    x=ServiceListing(owner_telegram_id=uid,**p.model_dump());db.add(x);db.commit();db.refresh(x);return dump(x)

@app.get("/api/partners")
def partners(q:Optional[str]=None,db:Session=Depends(get_db)):
    xs=list(db.scalars(select(PartnerPost).where(PartnerPost.status=="published").order_by(PartnerPost.id.desc()).limit(100)))
    if q:xs=[x for x in xs if q.lower() in x.company_name.lower() or q in (x.inn or "")]
    return [dump(x) for x in xs]
@app.post("/api/partners")
def create_partner(p:PartnerIn,uid:int=Depends(get_telegram_user),db:Session=Depends(get_db)):
    x=PartnerPost(owner_telegram_id=uid,**p.model_dump(),status="pending_moderation");db.add(x);db.commit();db.refresh(x)
    return {"id":x.id,"status":x.status,"message":"Передано на модерацию"}

@app.get("/api/meta")
def meta():
    return {"name":"CargoLink","sections":["Найти груз","Разместить заявку","Свободные автомобили","Помощь на дорогах","Партнёры","Мой профиль","Мои заявки"],"service_categories":["АЗС","СТО","Шиномонтаж"]}
