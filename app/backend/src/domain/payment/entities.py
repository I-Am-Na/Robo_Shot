from dataclasses import dataclass
from datetime import datetime


@dataclass
class Payment:
    """차량 방문(결제) 기록. 방문할 때마다 1건씩 쌓인다."""

    car_num: str
    paid_at: datetime
    amount: int = 0
    id: int | None = None
