from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from db import Base

def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    telegram_id: Mapped[int]=mapped_column(Integer,unique=True,index=True)
    username: Mapped[str|None]=mapped_column(String(64),nullable=True)
    fio: Mapped[str]=mapped_column(String(200),default="")
    phone: Mapped[str|None]=mapped_column(String(32),nullable=True)
    organization: Mapped[str|None]=mapped_column(String(200),nullable=True)
    inn: Mapped[str|None]=mapped_column(String(12),nullable=True)
    specialization: Mapped[str|None]=mapped_column(String(120),nullable=True)
    phone_private: Mapped[bool]=mapped_column(Boolean,default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Load(Base):
    __tablename__="loads"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    owner_telegram_id: Mapped[int]=mapped_column(Integer,index=True)
    origin: Mapped[str]=mapped_column(String(200))
    destination: Mapped[str]=mapped_column(String(200))
    vehicle_type: Mapped[str]=mapped_column(String(100),default="Не указан")
    cargo_type: Mapped[str]=mapped_column(String(100),default="Не указан")
    weight_t: Mapped[str|None]=mapped_column(String(30),nullable=True)
    volume_m3: Mapped[str|None]=mapped_column(String(30),nullable=True)
    hazard_class: Mapped[str]=mapped_column(String(30),default="Неопасный")
    rate_type: Mapped[str]=mapped_column(String(30),default="request")
    rate_amount: Mapped[str|None]=mapped_column(String(30),nullable=True)
    vat: Mapped[str]=mapped_column(String(20),default="Не указано")
    comment: Mapped[str|None]=mapped_column(Text,nullable=True)
    status: Mapped[str]=mapped_column(String(30),default="active",index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Offer(Base):
    __tablename__="offers"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    load_id: Mapped[int]=mapped_column(Integer,index=True)
    carrier_telegram_id: Mapped[int]=mapped_column(Integer,index=True)
    amount: Mapped[str]=mapped_column(String(30))
    vat: Mapped[str]=mapped_column(String(20),default="Не указано")
    comment: Mapped[str|None]=mapped_column(Text,nullable=True)
    status: Mapped[str]=mapped_column(String(30),default="pending")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Vehicle(Base):
    __tablename__="vehicles"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    owner_telegram_id: Mapped[int]=mapped_column(Integer,index=True)
    category: Mapped[str]=mapped_column(String(30))
    tonnage: Mapped[str]=mapped_column(String(30))
    description: Mapped[str]=mapped_column(Text)
    expires_on: Mapped[str]=mapped_column(String(20))
    status: Mapped[str]=mapped_column(String(30),default="active",index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class ServiceListing(Base):
    __tablename__="service_listings"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    owner_telegram_id: Mapped[int]=mapped_column(Integer,index=True)
    category: Mapped[str]=mapped_column(String(30))
    city: Mapped[str]=mapped_column(String(150),index=True)
    title: Mapped[str]=mapped_column(String(200))
    address: Mapped[str|None]=mapped_column(String(300),nullable=True)
    contacts: Mapped[str|None]=mapped_column(String(300),nullable=True)
    description: Mapped[str|None]=mapped_column(Text,nullable=True)
    status: Mapped[str]=mapped_column(String(30),default="active",index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class PartnerPost(Base):
    __tablename__="partner_posts"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    owner_telegram_id: Mapped[int]=mapped_column(Integer,index=True)
    company_name: Mapped[str]=mapped_column(String(200),index=True)
    inn: Mapped[str|None]=mapped_column(String(12),nullable=True)
    description: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(30),default="pending_moderation",index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
