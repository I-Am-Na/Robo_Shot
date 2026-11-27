from typing import Literal

from pydantic import BaseModel


class VisitCarInput(BaseModel):
    car_num: str
    is_line: bool
    line_num: Literal[1, 2]


class VisitCarOutput(BaseModel):
    success: bool
    message: str
