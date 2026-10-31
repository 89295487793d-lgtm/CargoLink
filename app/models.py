from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CargoRequest(Base):
    __tablename__ = "cargo_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    origin: Mapped[str] = mapped_column(String(300))
    destination: Mapped[str] = mapped_column(String(300))
    cargo: Mapped[str] = mapped_column(String(300))
    weight_tons: Mapped[float] = mapped_column(Float)
    vehicle_type: Mapped[str] = mapped_column(String(200))
    pickup_date: Mapped[str] = mapped_column(String(100))
    price_rub: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())



class CarrierOffer(Base):
    __tablename__ = "carrier_offers"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("cargo_requests.id", ondelete="CASCADE"), index=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    price_rub: Mapped[float] = mapped_column(Float)
    vat_mode: Mapped[str] = mapped_column(String(20))
    vehicle_type: Mapped[str] = mapped_column(String(200))
    completion_date: Mapped[str] = mapped_column(String(100))
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
