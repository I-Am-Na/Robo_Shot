from typing import Literal

from pydantic import BaseModel

from src.domain.car.value_objects import FuelType


class VisitCarInput(BaseModel):
    car_num: str
    is_line: bool
    line_num: Literal[1, 2]
    fuel_type: FuelType | None = None


class VisitCarOutput(BaseModel):
    success: bool
    message: str
