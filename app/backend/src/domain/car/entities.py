from dataclasses import dataclass
from datetime import datetime

from src.domain.car.value_objects import FuelType


@dataclass
class Car:
    """차량 Aggregate Root. car_num 당 1건을 유지한다."""

    car_num: str
    is_line: bool
    line_num: int
    updated_at: datetime
    fuel_type: FuelType | None = None
    id: int | None = None

    def update(
        self,
        is_line: bool,
        line_num: int,
        updated_at: datetime,
        fuel_type: FuelType | None = None,
    ) -> None:
        self.is_line = is_line
        self.line_num = line_num
        self.updated_at = updated_at
        # 유종은 확인된 값이 들어왔을 때만 갱신한다. 없으면 저장된 값을 유지한다.
        if fuel_type is not None:
            self.fuel_type = fuel_type
