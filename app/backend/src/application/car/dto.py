from datetime import datetime
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
    status: str | None = None


class CompleteFuelingOutput(BaseModel):
    success: bool
    message: str
    next_car_num: str | None = None  # 이어서 ready가 된 차량. 없으면 None


class CarSummary(BaseModel):
    car_num: str
    is_line: bool
    line_num: int
    fuel_type: FuelType | None
    status: str | None
    updated_at: datetime
    status_updated_at: datetime | None


class RobotTask(BaseModel):
    start: bool  # True면 주유 시작
    car_num: str | None = None
    line_num: int | None = None
    fuel_type: FuelType | None = None
    amount: int | None = None
