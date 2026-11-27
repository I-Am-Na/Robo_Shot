from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.car.entities import Car
from src.domain.car.repositories import CarRepository
from src.domain.payment.entities import Payment
from src.domain.payment.repositories import PaymentRepository
from src.infrastructure.db.models import CarModel, PaymentModel


class SqlAlchemyCarRepository(CarRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_car_num(self, car_num: str) -> Car | None:
        row = await self._session.scalar(select(CarModel).where(CarModel.car_num == car_num))
        if row is None:
            return None
        return Car(
            id=row.id,
            car_num=row.car_num,
            is_line=row.is_line,
            line_num=row.line_num,
            updated_at=row.updated_at,
        )

    async def save(self, car: Car) -> Car:
        if car.id is None:
            row = CarModel(
                car_num=car.car_num, is_line=car.is_line, line_num=car.line_num, updated_at=car.updated_at
            )
            self._session.add(row)
        else:
            row = await self._session.get(CarModel, car.id)
            row.is_line = car.is_line
            row.line_num = car.line_num
            row.updated_at = car.updated_at
        await self._session.flush()
        car.id = row.id
        return car


class SqlAlchemyPaymentRepository(PaymentRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, payment: Payment) -> Payment:
        row = PaymentModel(car_num=payment.car_num, amount=payment.amount, paid_at=payment.paid_at)
        self._session.add(row)
        await self._session.flush()
        payment.id = row.id
        return payment
