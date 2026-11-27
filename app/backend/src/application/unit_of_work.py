from abc import ABC, abstractmethod

from src.domain.car.repositories import CarRepository
from src.domain.payment.repositories import PaymentRepository
from src.domain.robot_action.repositories import RobotActionRepository


class UnitOfWork(ABC):
    """여러 리포지토리 작업을 하나의 트랜잭션으로 묶는다."""

    cars: CarRepository
    payments: PaymentRepository
    robot_actions: RobotActionRepository

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
