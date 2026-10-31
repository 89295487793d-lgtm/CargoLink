from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(300), index=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    tax_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    company_type: Mapped[str] = mapped_column(String(30), default="legal_entity")
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class CompanyMember(Base):
    __tablename__ = "company_members"
    __table_args__ = (UniqueConstraint("company_id", "user_id", name="uq_company_member"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class DangerousGood(Base):
    __tablename__ = "dangerous_goods"
    id: Mapped[int] = mapped_column(primary_key=True)
    un_number: Mapped[str] = mapped_column(String(4), unique=True, index=True)
    proper_shipping_name: Mapped[str] = mapped_column(String(300))
    hazard_class: Mapped[str] = mapped_column(String(10), index=True)
    subsidiary_risks: Mapped[str | None] = mapped_column(String(100), nullable=True)
    packing_group: Mapped[str | None] = mapped_column(String(10), nullable=True)
    physical_state: Mapped[str] = mapped_column(String(20), default="liquid")
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rules_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    registration_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(50), default="road_tanker")
    capacity_tons: Mapped[float | None] = mapped_column(Float, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    country_code: Mapped[str] = mapped_column(String(2), default="RU")

class TankSpec(Base):
    __tablename__ = "tank_specs"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), unique=True, index=True)
    total_volume_m3: Mapped[float] = mapped_column(Float)
    section_count: Mapped[int] = mapped_column(Integer, default=1)
    material: Mapped[str | None] = mapped_column(String(80), nullable=True)
    insulated: Mapped[bool] = mapped_column(Boolean, default=False)
    heating: Mapped[bool] = mapped_column(Boolean, default=False)
    pump: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_un_numbers: Mapped[list] = mapped_column(JSON, default=list)
    technical_data: Mapped[dict] = mapped_column(JSON, default=dict)

class Driver(Base):
    __tablename__ = "drivers"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    country_code: Mapped[str] = mapped_column(String(2))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

class ComplianceDocument(Base):
    __tablename__ = "compliance_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(30), index=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    document_type: Mapped[str] = mapped_column(String(80), index=True)
    document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="pending")

class CompatibilityCheck(Base):
    __tablename__ = "compatibility_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("cargo_requests.id", ondelete="CASCADE"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), index=True)
    result: Mapped[str] = mapped_column(String(30), index=True)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    rules_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Shipment(Base):
    __tablename__ = "shipments"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("cargo_requests.id"), unique=True, index=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("carrier_offers.id"), unique=True, index=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="confirmed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
