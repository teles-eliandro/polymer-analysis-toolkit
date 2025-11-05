from pydantic import BaseModel, Field
from typing import List

class MolecularInput(BaseModel):
    masses: List[float] = Field(..., example=[1000, 2000, 5000])
    weight_fractions: List[float] = Field(..., example=[0.2, 0.5, 0.3])

class MolecularResult(BaseModel):
    Mn: float
    Mw: float
    dispersity: float  # Đ

class ErrorResponse(BaseModel):
    detail: str