import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta

from src.application.car.dto import (
    CarSummary,
    CompleteFuelingOutput,
    RobotTask,
    VisitCarInput,
    VisitCarOutput,
)
from src.application.unit_of_work import UnitOfWork
from src.domain.car.entities import Car
from src.domain.car.exceptions import CarNotFoundError
from src.domain.car.value_objects import BUSY_STATUSES, STATUS_PAID, STATUS_WAITING, FuelType
from src.domain.payment.entities import Payment


class VisitCarUseCase:
    """차량 감지(YOLO) 처리.

    - car: car_num 기준으로 없으면 생성, 있으면 업데이트
    - payment: 요청마다 1건 추가
    - 대기열: 라인에 정상 진입한 차량은 ready(로봇이 비어 있음) 또는 waiting(앞 차량 주유 중)이 된다.
      이미 대기열에 있는 차량은 상태를 바꾸지 않는다.

    queue_lock: 1번·2번 라인에서 동시에 차량이 들어와도 ready가 2대가 되지 않도록
    대기열 판단과 저장을 직렬화한다. (uvicorn 워커 1개 기준)
    """

    def __init__(
        self,
        uow: UnitOfWork,
        clock: Callable[[], datetime],
        queue_lock: asyncio.Lock,
        done_window: timedelta,
    ):
        self._uow = uow
        self._clock = clock
        self._lock = queue_lock
        self._done_window = done_window

    async def execute(self, data: VisitCarInput) -> VisitCarOutput:
        async with self._lock:
            now = self._clock()
            try:
                car = await self._uow.cars.find_by_car_num(data.car_num)
                if car is None:
                    car = Car.register(
                        car_num=data.car_num,
                        is_line=data.is_line,
                        line_num=data.line_num,
                        detected_at=now,
                        fuel_type=data.fuel_type,
                    )
                    message = "created"
                else:
                    car.update(
                        is_line=data.is_line,
                        line_num=data.line_num,
                        updated_at=now,
                        fuel_type=data.fuel_type,
                    )
                    message = "updated"

                if car.should_enter_queue(now, self._done_window):
                    robot_busy = False
                    for busy_status in BUSY_STATUSES:
                        if await self._uow.cars.list_by_status(busy_status):
                            robot_busy = True
                            break
                    car.enter_queue(robot_busy=robot_busy, now=now)

                await self._uow.cars.save(car)
                await self._uow.payments.add(Payment(car_num=car.car_num, paid_at=now))
                await self._uow.commit()
            except Exception:
                await self._uow.rollback()
                raise
        return VisitCarOutput(success=True, message=message, status=car.status)


class CompleteFuelingUseCase:
    """주유 완료. 해당 차량은 done이 되고, 가장 먼저 기다린 waiting 차량이 ready가 된다."""

    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime], queue_lock: asyncio.Lock):
        self._uow = uow
        self._clock = clock
        self._lock = queue_lock

    async def execute(self, car_num: str) -> CompleteFuelingOutput:
        async with self._lock:
            now = self._clock()
            try:
                car = await self._uow.cars.find_by_car_num(car_num)
                if car is None:
                    raise CarNotFoundError(car_num)
                car.complete_fueling(now)
                await self._uow.cars.save(car)

                next_car = None
                waiting = await self._uow.cars.list_by_status(STATUS_WAITING)
                if waiting:
                    next_car = waiting[0]
                    next_car.promote(now)
                    await self._uow.cars.save(next_car)

                await self._uow.commit()
            except Exception:
                await self._uow.rollback()
                raise
        return CompleteFuelingOutput(
            success=True,
            message="fueling completed",
            next_car_num=next_car.car_num if next_car else None,
        )


class ListCarsUseCase:
    """대시보드 polling용 차량 목록. 최근 감지된 차량부터."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, limit: int) -> list[CarSummary]:
        cars = await self._uow.cars.list_recent(limit)
        return [
            CarSummary(
                car_num=c.car_num,
                is_line=c.is_line,
                line_num=c.line_num,
                fuel_type=c.fuel_type,
                status=c.status,
                updated_at=c.updated_at,
                status_updated_at=c.status_updated_at,
            )
            for c in cars
        ]


class OrderFuelTypeUseCase:
    """음성 주문에서 인식한 유종을 저장한다. 금액은 저장하지 않는다(결제 QR에만 사용)."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, car_num: str, fuel_type: FuelType) -> None:
        try:
            car = await self._uow.cars.find_by_car_num(car_num)
            if car is None:
                raise CarNotFoundError(car_num)
            car.order_fuel_type(fuel_type)
            await self._uow.cars.save(car)
            await self._uow.commit()
        except Exception:
            await self._uow.rollback()
            raise


class PayUseCase:
    """QR 결제 완료. 차량은 paid가 되고, 이번 방문기록(payment)에 결제 금액을 남긴다.

    paid 차량은 로봇이 GET /robot/task polling으로 받아 주유를 시작한다.
    """

    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime], queue_lock: asyncio.Lock):
        self._uow = uow
        self._clock = clock
        self._lock = queue_lock

    async def execute(self, car_num: str, fuel_type: FuelType, amount: int) -> None:
        async with self._lock:
            try:
                car = await self._uow.cars.find_by_car_num(car_num)
                if car is None:
                    raise CarNotFoundError(car_num)
                car.pay(fuel_type, self._clock())
                await self._uow.cars.save(car)

                payment = await self._uow.payments.find_latest_by_car_num(car_num)
                if payment is None:
                    await self._uow.payments.add(Payment(car_num=car_num, paid_at=self._clock(), amount=amount))
                else:
                    payment.amount = amount
                    await self._uow.payments.save(payment)
                await self._uow.commit()
            except Exception:
                await self._uow.rollback()
                raise


class GetRobotTaskUseCase:
    """로봇 polling: 결제가 끝나 주유를 시작해야 하는 차량이 있는지 알려준다."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self) -> RobotTask:
        paid = await self._uow.cars.list_by_status(STATUS_PAID)
        if not paid:
            return RobotTask(start=False)
        car = paid[0]
        payment = await self._uow.payments.find_latest_by_car_num(car.car_num)
        return RobotTask(
            start=True,
            car_num=car.car_num,
            line_num=car.line_num,
            fuel_type=car.fuel_type,
            amount=payment.amount if payment else None,
        )
