from collections.abc import Callable
from datetime import datetime

from src.application.car.dto import VisitCarInput, VisitCarOutput
from src.application.unit_of_work import UnitOfWork
from src.domain.car.entities import Car
from src.domain.payment.entities import Payment


class VisitCarUseCase:
    """차량 방문 처리.

    - car: car_num 기준으로 없으면 생성, 있으면 업데이트
    - payment: 방문할 때마다 1건 추가
    두 작업은 하나의 트랜잭션으로 처리한다.
    """

    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime]):
        self._uow = uow
        self._clock = clock

    async def execute(self, data: VisitCarInput) -> VisitCarOutput:
        now = self._clock()
        try:
            car = await self._uow.cars.find_by_car_num(data.car_num)
            if car is None:
                car = Car(car_num=data.car_num, is_line=data.is_line, line_num=data.line_num, updated_at=now)
                message = "created"
            else:
                car.update(is_line=data.is_line, line_num=data.line_num, updated_at=now)
                message = "updated"
            await self._uow.cars.save(car)
            await self._uow.payments.add(Payment(car_num=car.car_num, paid_at=now))
            await self._uow.commit()
        except Exception:
            await self._uow.rollback()
            raise
        return VisitCarOutput(success=True, message=message)
