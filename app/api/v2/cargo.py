from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from app.database import SessionLocal
from app.domain_models import DangerousGood
router = APIRouter(tags=["CargoLink v2 · Cargo"])

@router.get("/cargo/dangerous-goods")
async def search_dangerous_goods(q: str = "", limit: int = 30):
    limit = max(1, min(limit, 100))
    async with SessionLocal() as session:
        stmt = select(DangerousGood).where(DangerousGood.physical_state == "liquid").order_by(DangerousGood.un_number).limit(limit)
        if q.strip():
            term = q.strip()
            stmt = stmt.where((DangerousGood.un_number.ilike(f"%{term}%")) | (DangerousGood.proper_shipping_name.ilike(f"%{term}%")))
        rows = (await session.execute(stmt)).scalars().all()
    return {"items":[{"un_number":r.un_number,"proper_shipping_name":r.proper_shipping_name,"hazard_class":r.hazard_class,
        "subsidiary_risks":r.subsidiary_risks,"packing_group":r.packing_group,"verified":r.verified} for r in rows]}

@router.get("/cargo/dangerous-goods/{un_number}")
async def get_dangerous_good(un_number: str):
    normalized = un_number.upper().replace("UN", "").strip()
    async with SessionLocal() as session:
        row = (await session.execute(select(DangerousGood).where(DangerousGood.un_number == normalized))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Dangerous good not found")
    return {"un_number":row.un_number,"proper_shipping_name":row.proper_shipping_name,"hazard_class":row.hazard_class,
        "subsidiary_risks":row.subsidiary_risks,"packing_group":row.packing_group,"physical_state":row.physical_state,
        "properties":row.properties,"verified":row.verified,"rules_version":row.rules_version}
