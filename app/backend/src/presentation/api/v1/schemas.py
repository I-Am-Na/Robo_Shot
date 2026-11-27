from typing import Literal

from pydantic import BaseModel, Field

from src.domain.car.value_objects import FuelType


class CarVisitRequest(BaseModel):
    car_num: str = Field(..., min_length=1, max_length=20, examples=["12가3456"])
    is_line: bool
    line_num: Literal[1, 2]
    fuel_type: FuelType | None = Field(
        default=None, description="휘발유 또는 경유. 생략하면 저장된 값을 유지한다."
    )


class CarVisitResponse(BaseModel):
    success: bool
    message: str
