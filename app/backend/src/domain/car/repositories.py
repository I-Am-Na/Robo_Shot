from abc import ABC, abstractmethod

from src.domain.car.entities import Car


class CarRepository(ABC):
    @abstractmethod
    async def find_by_car_num(self, car_num: str) -> Car | None: ...

    @abstractmethod
    async def save(self, car: Car) -> Car: ...

    @abstractmethod
    async def list_recent(self, limit: int) -> list[Car]:
        """최근 감지된 순서(updated_at 내림차순)로 최대 limit건."""

    @abstractmethod
    async def list_by_status(self, status: str) -> list[Car]:
        """해당 status 차량을 상태가 바뀐 순서(status_updated_at 오름차순, 먼저 온 차량 먼저)로."""
