from abc import ABC, abstractmethod

from src.domain.payment.entities import Payment


class PaymentRepository(ABC):
    @abstractmethod
    async def add(self, payment: Payment) -> Payment: ...
