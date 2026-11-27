from collections.abc import Callable
from datetime import datetime

from src.application.robot_action.dto import CreateRobotActionInput, RobotActionDetail, UpdateRobotActionInput
from src.application.unit_of_work import UnitOfWork
from src.domain.car.exceptions import CarNotFoundError
from src.domain.robot_action.entities import RobotAction
from src.domain.robot_action.exceptions import RobotActionNotFoundError


def _detail(a: RobotAction) -> RobotActionDetail:
    return RobotActionDetail(
        id=a.id,
        car_num=a.car_num,
        line_num=a.line_num,
        fuel_type=a.fuel_type,
        amount=a.amount,
        status=a.status,
        step=a.step,
        step_index=a.step_index,
        step_count=a.step_count,
        message=a.message,
        created_at=a.created_at,
        started_at=a.started_at,
        finished_at=a.finished_at,
    )


class CreateRobotActionUseCase:
    """중간 노드가 로봇에 주유 goal을 보낼 때 기록을 만든다 (status=requested)."""

    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime]):
        self._uow = uow
        self._clock = clock

    async def execute(self, data: CreateRobotActionInput) -> RobotActionDetail:
        try:
            if await self._uow.cars.find_by_car_num(data.car_num) is None:
                raise CarNotFoundError(data.car_num)
            action = RobotAction(
                car_num=data.car_num,
                line_num=data.line_num,
                fuel_type=data.fuel_type,
                amount=data.amount,
                created_at=self._clock(),
            )
            await self._uow.robot_actions.add(action)
            await self._uow.commit()
        except Exception:
            await self._uow.rollback()
            raise
        return _detail(action)


class UpdateRobotActionUseCase:
    """수락·단계 진행(feedback)·결과를 기록한다."""

    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime]):
        self._uow = uow
        self._clock = clock

    async def execute(self, action_id: int, data: UpdateRobotActionInput) -> RobotActionDetail:
        try:
            action = await self._uow.robot_actions.get(action_id)
            if action is None:
                raise RobotActionNotFoundError(action_id)
            action.apply(
                status=data.status,
                now=self._clock(),
                step=data.step,
                step_index=data.step_index,
                step_count=data.step_count,
                message=data.message,
            )
            await self._uow.robot_actions.save(action)
            await self._uow.commit()
        except Exception:
            await self._uow.rollback()
            raise
        return _detail(action)


class ListRobotActionsUseCase:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def execute(self, limit: int, car_num: str | None = None) -> list[RobotActionDetail]:
        return [_detail(a) for a in await self._uow.robot_actions.list_recent(limit, car_num)]
