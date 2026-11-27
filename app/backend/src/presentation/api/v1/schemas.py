from typing import Literal

from pydantic import BaseModel, Field


class CarVisitRequest(BaseModel):
    car_num: str = Field(..., min_length=1, max_length=20, examples=["12가3456"])
    is_line: bool
    line_num: Literal[1, 2]


class CarVisitResponse(BaseModel):
    success: bool
    message: str
