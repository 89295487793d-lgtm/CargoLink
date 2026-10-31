from fastapi import APIRouter
from app.api.v2.compatibility import router as compatibility_router
from app.api.v2.cargo import router as cargo_router
router = APIRouter(prefix="/api/v2")
router.include_router(compatibility_router)
router.include_router(cargo_router)
