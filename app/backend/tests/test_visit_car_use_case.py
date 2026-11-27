from datetime import datetime

import pytest

from src.application.car.dto import VisitCarInput
from src.application.car.use_cases import VisitCarUseCase
from src.application.unit_of_work import UnitOfWork
from src.domain.car.entities import Car
from src.domain.car.repositories import CarRepository
from src.domain.car.value_objects import FuelType
from src.domain.payment.entities import Payment
from src.domain.payment.repositories import PaymentRepository


class InMemoryCarRepository(CarRepository):
    def __init__(self):
        self.items: dict[str, Car] = {}

    async def find_by_car_num(self, car_num: str) -> Car | None:
        return self.items.get(car_num)

    async def save(self, car: Car) -> Car:
        if car.id is None:
            car.id = len(self.items) + 1
        self.items[car.car_num] = car
        return car


class InMemoryPaymentRepository(PaymentRepository):
    def __init__(self, fail: bool = False):
        self.items: list[Payment] = []
        self.fail = fail

    async def add(self, payment: Payment) -> Payment:
        if self.fail:
            raise RuntimeError("db error")
        payment.id = len(self.items) + 1
        self.items.append(payment)
        return payment


class FakeUnitOfWork(UnitOfWork):
    def __init__(self, payments: InMemoryPaymentRepository | None = None):
        self.cars = InMemoryCarRepository()
        self.payments = payments or InMemoryPaymentRepository()
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


T1 = datetime(2026, 11, 27, 10, 0, 0)
T2 = datetime(2026, 11, 27, 11, 30, 15)


@pytest.mark.asyncio
async def test_creates_car_and_adds_payment_when_car_not_exists():
    uow = FakeUnitOfWork()
    out = await VisitCarUseCase(uow, clock=lambda: T1).execute(
        VisitCarInput(car_num="12가3456", is_line=True, line_num=1)
    )
    assert out.success is True
    assert out.message == "created"
    car = uow.cars.items["12가3456"]
    assert (car.is_line, car.line_num, car.updated_at) == (True, 1, T1)
    assert len(uow.payments.items) == 1
    assert uow.payments.items[0].car_num == "12가3456"
    assert uow.payments.items[0].paid_at == T1
    assert uow.committed


@pytest.mark.asyncio
async def test_updates_car_and_adds_another_payment_when_car_exists():
    uow = FakeUnitOfWork()
    uow.cars.items["12가3456"] = Car(id=1, car_num="12가3456", is_line=True, line_num=1, updated_at=T1)
    out = await VisitCarUseCase(uow, clock=lambda: T2).execute(
        VisitCarInput(car_num="12가3456", is_line=False, line_num=2)
    )
    assert out.message == "updated"
    car = uow.cars.items["12가3456"]
    assert (car.is_line, car.line_num, car.updated_at) == (False, 2, T2)
    assert len(uow.cars.items) == 1
    assert len(uow.payments.items) == 1
    assert uow.payments.items[0].paid_at == T2


@pytest.mark.asyncio
async def test_new_car_without_fuel_type_is_saved_as_none():
    uow = FakeUnitOfWork()
    await VisitCarUseCase(uow, clock=lambda: T1).execute(
        VisitCarInput(car_num="12가3456", is_line=True, line_num=1)
    )
    assert uow.cars.items["12가3456"].fuel_type is None


@pytest.mark.asyncio
async def test_fuel_type_is_saved_and_kept_when_omitted():
    uow = FakeUnitOfWork()
    use_case = VisitCarUseCase(uow, clock=lambda: T1)
    await use_case.execute(VisitCarInput(car_num="12가3456", is_line=True, line_num=1, fuel_type="경유"))
    assert uow.cars.items["12가3456"].fuel_type is FuelType.DIESEL

    await use_case.execute(VisitCarInput(car_num="12가3456", is_line=True, line_num=2))
    assert uow.cars.items["12가3456"].fuel_type is FuelType.DIESEL

    await use_case.execute(VisitCarInput(car_num="12가3456", is_line=True, line_num=2, fuel_type="휘발유"))
    assert uow.cars.items["12가3456"].fuel_type is FuelType.GASOLINE


def test_invalid_fuel_type_is_rejected():
    with pytest.raises(ValueError):
        VisitCarInput(car_num="12가3456", is_line=True, line_num=1, fuel_type="LPG")


@pytest.mark.asyncio
async def test_rolls_back_when_payment_fails():
    uow = FakeUnitOfWork(payments=InMemoryPaymentRepository(fail=True))
    with pytest.raises(RuntimeError):
        await VisitCarUseCase(uow, clock=lambda: T1).execute(
            VisitCarInput(car_num="12가3456", is_line=True, line_num=1)
        )
    assert uow.rolled_back
    assert not uow.committed
