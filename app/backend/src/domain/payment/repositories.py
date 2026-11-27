from abc import ABC, abstractmethod

from src.domain.payment.entities import Payment


class PaymentRepository(ABC):
    @abstractmethod
    async def add(self, payment: Payment) -> Payment: ...

    @abstractmethod
    async def find_latest_by_car_num(self, car_num: str) -> Payment | None:
        """해당 차량의 가장 최근 방문기록."""

    @abstractmethod
    async def save(self, payment: Payment) -> Payment:
        """기존 방문기록 수정 (결제 금액 기록)."""
