from dataclasses import dataclass
from datetime import datetime


@dataclass
class Car:
    """차량 Aggregate Root. car_num 당 1건을 유지한다."""

    car_num: str
    is_line: bool
    line_num: int
    updated_at: datetime
    id: int | None = None

    def update(self, is_line: bool, line_num: int, updated_at: datetime) -> None:
        self.is_line = is_line
        self.line_num = line_num
        self.updated_at = updated_at
