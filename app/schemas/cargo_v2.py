from pydantic import BaseModel, Field

class CompatibilityCargo(BaseModel):
    un_number: str = Field(pattern=r"^(UN)?\s?\d{4}$")
    hazard_class: str = Field(min_length=1, max_length=10)
    weight_tons: float = Field(gt=0)
    volume_m3: float | None = Field(default=None, gt=0)
    pump_required: bool = False

class CompatibilityTank(BaseModel):
    total_volume_m3: float = Field(gt=0)
    pump: bool = False
    allowed_un_numbers: list[str] = Field(default_factory=list)

class CompatibilityCheckInput(BaseModel):
    cargo: CompatibilityCargo
    vehicle: dict = Field(default_factory=dict)
    tank: CompatibilityTank
    documents: list[dict] = Field(default_factory=list)
    rules_version: str | None = None
