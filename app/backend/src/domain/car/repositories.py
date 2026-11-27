from abc import ABC, abstractmethod

from src.domain.car.entities import Car


class CarRepository(ABC):
    @abstractmethod
    async def find_by_car_num(self, car_num: str) -> Car | None: ...

    @abstractmethod
    async def save(self, car: Car) -> Car: ...
