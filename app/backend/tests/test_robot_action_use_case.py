from datetime import datetime, timedelta

import pytest

from src.application.robot_action.dto import CreateRobotActionInput, UpdateRobotActionInput
from src.application.robot_action.use_cases import (
    CreateRobotActionUseCase,
    ListRobotActionsUseCase,
    UpdateRobotActionUseCase,
)
from src.domain.car.entities import Car
from src.domain.car.exceptions import CarNotFoundError
from src.domain.robot_action.exceptions import InvalidRobotActionTransition, RobotActionNotFoundError
from tests.test_visit_car_use_case import Clock, FakeUnitOfWork

T0 = datetime(2026, 11, 27, 10, 0, 0)


def setup():
    uow = FakeUnitOfWork()
    for n in ("11가1111", "22나2222"):
        uow.cars.items[n] = Car(id=len(uow.cars.items) + 1, car_num=n, is_line=True, line_num=1, updated_at=T0)
    clock = Clock(T0)
    return uow, clock, CreateRobotActionUseCase(uow, clock), UpdateRobotActionUseCase(uow, clock)


def goal(car_num="11가1111"):
    return CreateRobotActionInput(car_num=car_num, line_num=1, fuel_type="휘발유", amount=50000)


def upd(status, **kw):
    return UpdateRobotActionInput(status=status, **kw)


@pytest.mark.asyncio
async def test_full_success_flow_records_times_and_steps():
    uow, clock, create, update = setup()
    a = await create.execute(goal())
    assert (a.id, a.status, a.created_at, a.started_at) == (1, "requested", T0, None)

    clock.tick(1)
    a = await update.execute(a.id, upd("running"))
    assert (a.status, a.started_at) == ("running", T0 + timedelta(seconds=1))

    clock.tick(1)
    a = await update.execute(a.id, upd("running", step="노즐 삽입", step_index=4, step_count=7))
    assert (a.step, a.step_index, a.step_count, a.started_at) == ("노즐 삽입", 4, 7, T0 + timedelta(seconds=1))

    clock.tick(5)
    a = await update.execute(a.id, upd("succeeded", message="fueling completed"))
    assert (a.status, a.message, a.finished_at) == ("succeeded", "fueling completed", T0 + timedelta(seconds=7))
    assert a.step == "노즐 삽입"  # 마지막 단계 유지


@pytest.mark.asyncio
async def test_rejected_and_failed():
    uow, clock, create, update = setup()
    a = await create.execute(goal())
    a = await update.execute(a.id, upd("rejected", message="busy"))
    assert (a.status, a.started_at is None, a.finished_at) == ("rejected", True, T0)

    b = await create.execute(goal())
    await update.execute(b.id, upd("running"))
    b = await update.execute(b.id, upd("failed", step="노즐 파지", message="gripper error"))
    assert (b.status, b.step, b.message) == ("failed", "노즐 파지", "gripper error")


@pytest.mark.asyncio
async def test_finished_action_cannot_change():
    uow, clock, create, update = setup()
    a = await create.execute(goal())
    await update.execute(a.id, upd("running"))
    await update.execute(a.id, upd("succeeded"))
    with pytest.raises(InvalidRobotActionTransition):
        await update.execute(a.id, upd("failed"))
    assert uow.robot_actions.items[a.id].status == "succeeded"


@pytest.mark.asyncio
async def test_cannot_succeed_without_running():
    uow, clock, create, update = setup()
    a = await create.execute(goal())
    with pytest.raises(InvalidRobotActionTransition):
        await update.execute(a.id, upd("succeeded"))


@pytest.mark.asyncio
async def test_unknown_car_and_action():
    uow, clock, create, update = setup()
    with pytest.raises(CarNotFoundError):
        await create.execute(goal("99하9999"))
    with pytest.raises(RobotActionNotFoundError):
        await update.execute(999, upd("running"))


@pytest.mark.asyncio
async def test_list_recent_and_filter_by_car():
    uow, clock, create, update = setup()
    await create.execute(goal("11가1111"))
    await create.execute(goal("22나2222"))
    await create.execute(goal("11가1111"))
    actions = await ListRobotActionsUseCase(uow).execute(limit=10)
    assert [a.id for a in actions] == [3, 2, 1]
    mine = await ListRobotActionsUseCase(uow).execute(limit=10, car_num="11가1111")
    assert [a.id for a in mine] == [3, 1]
