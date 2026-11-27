import asyncio
from datetime import datetime, timedelta

import pytest

from src.application.car.dto import VisitCarInput
from src.application.car.use_cases import CompleteFuelingUseCase, ListCarsUseCase, VisitCarUseCase
from src.application.unit_of_work import UnitOfWork
from src.domain.car.entities import Car
from src.domain.car.exceptions import CarNotFoundError, CarNotReadyError
from src.domain.car.repositories import CarRepository
from src.domain.car.value_objects import FuelType
from src.domain.payment.entities import Payment
from src.domain.payment.repositories import PaymentRepository
from src.domain.robot_action.entities import RobotAction
from src.domain.robot_action.repositories import RobotActionRepository


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

    async def list_recent(self, limit: int) -> list[Car]:
        return sorted(self.items.values(), key=lambda c: c.updated_at, reverse=True)[:limit]

    async def list_by_status(self, status: str) -> list[Car]:
        cars = [c for c in self.items.values() if c.status == status]
        return sorted(cars, key=lambda c: (c.status_updated_at, c.id))


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

    async def find_latest_by_car_num(self, car_num: str) -> Payment | None:
        mine = [p for p in self.items if p.car_num == car_num]
        return max(mine, key=lambda p: (p.paid_at, p.id)) if mine else None

    async def save(self, payment: Payment) -> Payment:
        return payment  # 같은 객체를 들고 있으므로 수정 사항이 그대로 반영된다


class InMemoryRobotActionRepository(RobotActionRepository):
    def __init__(self):
        self.items: dict[int, RobotAction] = {}

    async def add(self, action: RobotAction) -> RobotAction:
        action.id = len(self.items) + 1
        self.items[action.id] = action
        return action

    async def get(self, action_id: int) -> RobotAction | None:
        return self.items.get(action_id)

    async def save(self, action: RobotAction) -> RobotAction:
        self.items[action.id] = action
        return action

    async def list_recent(self, limit: int, car_num: str | None = None) -> list[RobotAction]:
        rows = [a for a in self.items.values() if car_num is None or a.car_num == car_num]
        return sorted(rows, key=lambda a: a.id, reverse=True)[:limit]


class FakeUnitOfWork(UnitOfWork):
    def __init__(self, payments: InMemoryPaymentRepository | None = None):
        self.cars = InMemoryCarRepository()
        self.payments = payments or InMemoryPaymentRepository()
        self.robot_actions = InMemoryRobotActionRepository()
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class Clock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def tick(self, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)


T1 = datetime(2026, 11, 27, 10, 0, 0)
T2 = datetime(2026, 11, 27, 11, 30, 15)
DONE_WINDOW = timedelta(seconds=120)


class Station:
    """테스트용: 같은 uow/clock/lock을 공유하는 유스케이스 묶음."""

    def __init__(self, uow: FakeUnitOfWork | None = None, now: datetime = T1):
        self.uow = uow or FakeUnitOfWork()
        self.clock = Clock(now)
        lock = asyncio.Lock()
        self.visit_uc = VisitCarUseCase(self.uow, clock=self.clock, queue_lock=lock, done_window=DONE_WINDOW)
        self.complete_uc = CompleteFuelingUseCase(self.uow, clock=self.clock, queue_lock=lock)

    async def visit(self, car_num: str, is_line: bool = True, line_num: int = 1, **kw):
        return await self.visit_uc.execute(
            VisitCarInput(car_num=car_num, is_line=is_line, line_num=line_num, **kw)
        )

    async def complete(self, car_num: str):
        return await self.complete_uc.execute(car_num)

    def status(self, car_num: str) -> str | None:
        return self.uow.cars.items[car_num].status


# --- 기본 생성/업데이트 ---

@pytest.mark.asyncio
async def test_creates_car_and_adds_payment_when_car_not_exists():
    s = Station()
    out = await s.visit("12가3456")
    assert (out.success, out.message, out.status) == (True, "created", "ready")
    car = s.uow.cars.items["12가3456"]
    assert (car.is_line, car.line_num, car.updated_at) == (True, 1, T1)
    assert len(s.uow.payments.items) == 1
    assert s.uow.committed


@pytest.mark.asyncio
async def test_updates_car_and_adds_another_payment_when_car_exists():
    uow = FakeUnitOfWork()
    uow.cars.items["12가3456"] = Car(id=1, car_num="12가3456", is_line=True, line_num=1, updated_at=T1)
    s = Station(uow, now=T2)
    out = await s.visit("12가3456", is_line=False, line_num=2)
    assert out.message == "updated"
    car = uow.cars.items["12가3456"]
    assert (car.is_line, car.line_num, car.updated_at) == (False, 2, T2)
    assert len(uow.cars.items) == 1
    assert len(uow.payments.items) == 1


@pytest.mark.asyncio
async def test_fuel_type_is_saved_and_kept_when_omitted():
    s = Station()
    await s.visit("12가3456", fuel_type="경유")
    assert s.uow.cars.items["12가3456"].fuel_type is FuelType.DIESEL
    await s.visit("12가3456", line_num=2)
    assert s.uow.cars.items["12가3456"].fuel_type is FuelType.DIESEL


def test_invalid_fuel_type_is_rejected():
    with pytest.raises(ValueError):
        VisitCarInput(car_num="12가3456", is_line=True, line_num=1, fuel_type="LPG")


@pytest.mark.asyncio
async def test_rolls_back_when_payment_fails():
    s = Station(FakeUnitOfWork(payments=InMemoryPaymentRepository(fail=True)))
    with pytest.raises(RuntimeError):
        await s.visit("12가3456")
    assert s.uow.rolled_back
    assert not s.uow.committed


# --- 대기열 (로봇 1대, 라인 2개) ---

@pytest.mark.asyncio
async def test_not_in_line_car_does_not_enter_queue():
    s = Station()
    out = await s.visit("12가3456", is_line=False)
    assert out.status is None


@pytest.mark.asyncio
async def test_second_car_waits_while_first_is_ready():
    s = Station()
    assert (await s.visit("11가1111", line_num=1)).status == "ready"
    s.clock.tick(5)
    assert (await s.visit("22나2222", line_num=2)).status == "waiting"


@pytest.mark.asyncio
async def test_repeated_frames_do_not_change_queue_status():
    s = Station()
    await s.visit("11가1111", line_num=1)
    s.clock.tick(1)
    await s.visit("22나2222", line_num=2)
    for _ in range(3):
        s.clock.tick(1)
        await s.visit("11가1111", line_num=1)
        await s.visit("22나2222", line_num=2)
    assert (s.status("11가1111"), s.status("22나2222")) == ("ready", "waiting")


@pytest.mark.asyncio
async def test_complete_makes_first_car_done_and_next_waiting_car_ready():
    s = Station()
    await s.visit("11가1111", line_num=1)
    s.clock.tick(5)
    await s.visit("22나2222", line_num=2)
    s.clock.tick(5)
    await s.visit("33다3333", line_num=1)  # 3번째 차량도 대기

    s.clock.tick(60)
    out = await s.complete("11가1111")
    assert out.next_car_num == "22나2222"
    assert (s.status("11가1111"), s.status("22나2222"), s.status("33다3333")) == ("done", "ready", "waiting")

    s.clock.tick(60)
    out = await s.complete("22나2222")
    assert out.next_car_num == "33다3333"
    assert s.status("33다3333") == "ready"

    s.clock.tick(60)
    out = await s.complete("33다3333")
    assert out.next_car_num is None


@pytest.mark.asyncio
async def test_waiting_order_is_first_come_first_served_even_if_frames_keep_coming():
    s = Station()
    await s.visit("11가1111", line_num=1)
    s.clock.tick(1)
    await s.visit("22나2222", line_num=2)  # 먼저 대기
    s.clock.tick(1)
    await s.visit("33다3333", line_num=1)  # 나중에 대기
    s.clock.tick(1)
    await s.visit("22나2222", line_num=2)  # 먼저 온 차가 다시 감지돼도 순서는 그대로
    out = await s.complete("11가1111")
    assert out.next_car_num == "22나2222"


@pytest.mark.asyncio
async def test_new_car_is_ready_when_robot_is_free_after_complete():
    s = Station()
    await s.visit("11가1111")
    s.clock.tick(60)
    await s.complete("11가1111")
    s.clock.tick(10)
    assert (await s.visit("22나2222", line_num=2)).status == "ready"


@pytest.mark.asyncio
async def test_done_car_redetected_while_leaving_does_not_requeue():
    s = Station()
    await s.visit("11가1111")
    s.clock.tick(60)
    await s.complete("11가1111")
    s.clock.tick(30)  # 빠져나가는 중 다시 감지
    assert (await s.visit("11가1111")).status == "done"


@pytest.mark.asyncio
async def test_done_car_returning_later_requeues():
    s = Station()
    await s.visit("11가1111")
    s.clock.tick(60)
    await s.complete("11가1111")
    s.clock.tick(3600)  # 나중에 다시 방문
    assert (await s.visit("11가1111")).status == "ready"


@pytest.mark.asyncio
async def test_complete_waiting_car_is_rejected():
    s = Station()
    await s.visit("11가1111")
    await s.visit("22나2222", line_num=2)
    with pytest.raises(CarNotReadyError):
        await s.complete("22나2222")
    assert s.uow.rolled_back
    assert s.status("11가1111") == "ready"


@pytest.mark.asyncio
async def test_complete_unknown_car():
    with pytest.raises(CarNotFoundError):
        await Station().complete("99하9999")


@pytest.mark.asyncio
async def test_concurrent_arrivals_on_two_lines_make_only_one_ready():
    s = Station()
    outs = await asyncio.gather(s.visit("11가1111", line_num=1), s.visit("22나2222", line_num=2))
    assert sorted(o.status for o in outs) == ["ready", "waiting"]


def test_loading_car_does_not_overwrite_status():
    car = Car(id=1, car_num="12가3456", is_line=True, line_num=1, updated_at=T1, status="something")
    assert car.status == "something"


# --- GET /car (목록) ---

@pytest.mark.asyncio
async def test_list_cars_returns_recent_first_with_status():
    s = Station()
    await s.visit("11가1111", line_num=1)
    s.clock.tick(5)
    await s.visit("22나2222", line_num=2)

    cars = await ListCarsUseCase(s.uow).execute(limit=10)
    assert [(c.car_num, c.status) for c in cars] == [("22나2222", "waiting"), ("11가1111", "ready")]
    assert len(await ListCarsUseCase(s.uow).execute(limit=1)) == 1


# --- 음성 주문: 유종 저장 ---

@pytest.mark.asyncio
async def test_order_fuel_type_saves_only_for_ready_car():
    from src.application.car.use_cases import OrderFuelTypeUseCase

    s = Station()
    await s.visit("11가1111")
    s.clock.tick(1)
    await s.visit("22나2222", line_num=2)  # waiting

    await OrderFuelTypeUseCase(s.uow).execute("11가1111", FuelType.GASOLINE)
    assert s.uow.cars.items["11가1111"].fuel_type is FuelType.GASOLINE

    with pytest.raises(CarNotReadyError):
        await OrderFuelTypeUseCase(s.uow).execute("22나2222", FuelType.DIESEL)
    assert s.uow.cars.items["22나2222"].fuel_type is None

    with pytest.raises(CarNotFoundError):
        await OrderFuelTypeUseCase(s.uow).execute("99하9999", FuelType.DIESEL)



# --- 결제 완료 → 로봇 polling ---

def _pay_uc(s: "Station"):
    from src.application.car.use_cases import PayUseCase

    return PayUseCase(s.uow, clock=s.clock, queue_lock=asyncio.Lock())


def _robot_uc(s: "Station"):
    from src.application.car.use_cases import GetRobotTaskUseCase

    return GetRobotTaskUseCase(s.uow)


@pytest.mark.asyncio
async def test_robot_has_no_task_until_payment():
    s = Station()
    await s.visit("11가1111")
    task = await _robot_uc(s).execute()
    assert task.start is False


@pytest.mark.asyncio
async def test_pay_makes_car_paid_saves_amount_and_robot_starts():
    s = Station()
    await s.visit("11가1111", line_num=2)
    s.clock.tick(30)
    await _pay_uc(s).execute("11가1111", FuelType.GASOLINE, 50000)

    car = s.uow.cars.items["11가1111"]
    assert (car.status, car.fuel_type) == ("paid", FuelType.GASOLINE)
    assert s.uow.payments.items[-1].amount == 50000

    task = await _robot_uc(s).execute()
    assert (task.start, task.car_num, task.line_num, task.fuel_type, task.amount) == (
        True, "11가1111", 2, FuelType.GASOLINE, 50000,
    )


@pytest.mark.asyncio
async def test_new_car_waits_while_paid_car_is_fueling():
    s = Station()
    await s.visit("11가1111")
    await _pay_uc(s).execute("11가1111", FuelType.DIESEL, 30000)
    s.clock.tick(5)
    assert (await s.visit("22나2222", line_num=2)).status == "waiting"
    # 결제된 차량이 다시 감지돼도 paid 그대로
    assert (await s.visit("11가1111")).status == "paid"


@pytest.mark.asyncio
async def test_complete_paid_car_ends_task_and_promotes_next():
    s = Station()
    await s.visit("11가1111")
    s.clock.tick(1)
    await s.visit("22나2222", line_num=2)
    await _pay_uc(s).execute("11가1111", FuelType.GASOLINE, 50000)

    s.clock.tick(120)
    out = await s.complete("11가1111")
    assert out.next_car_num == "22나2222"
    assert s.status("22나2222") == "ready"
    assert (await _robot_uc(s).execute()).start is False  # 다음 차는 아직 결제 전


@pytest.mark.asyncio
async def test_pay_rejected_unless_ready():
    s = Station()
    await s.visit("11가1111")
    await s.visit("22나2222", line_num=2)  # waiting
    with pytest.raises(CarNotReadyError):
        await _pay_uc(s).execute("22나2222", FuelType.GASOLINE, 50000)
    await _pay_uc(s).execute("11가1111", FuelType.GASOLINE, 50000)
    with pytest.raises(CarNotReadyError):  # 이미 결제됨
        await _pay_uc(s).execute("11가1111", FuelType.GASOLINE, 50000)
    with pytest.raises(CarNotFoundError):
        await _pay_uc(s).execute("99하9999", FuelType.GASOLINE, 50000)
