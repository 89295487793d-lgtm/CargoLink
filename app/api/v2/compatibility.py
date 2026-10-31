from fastapi import APIRouter
from app.schemas.cargo_v2 import CompatibilityCheckInput
from app.services.compatibility import check_liquid_dangerous_goods
router = APIRouter(tags=["CargoLink v2 · Compatibility"])

@router.post("/compatibility/check")
async def check_compatibility(payload: CompatibilityCheckInput):
    return check_liquid_dangerous_goods(cargo=payload.cargo.model_dump(), vehicle=payload.vehicle,
        tank=payload.tank.model_dump(), documents=payload.documents)
