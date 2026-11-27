from datetime import datetime

from pydantic import BaseModel


class CreateRobotActionInput(BaseModel):
    car_num: str
    line_num: int
    fuel_type: str
    amount: int


class UpdateRobotActionInput(BaseModel):
    status: str
    step: str | None = None
    step_index: int | None = None
    step_count: int | None = None
    message: str | None = None


class RobotActionDetail(BaseModel):
    id: int
    car_num: str
    line_num: int
    fuel_type: str
    amount: int
    status: str
    step: str | None
    step_index: int | None
    step_count: int | None
    message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
