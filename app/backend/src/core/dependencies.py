import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.car.use_cases import (
    CompleteFuelingUseCase,
    GetRobotTaskUseCase,
    ListCarsUseCase,
    OrderFuelTypeUseCase,
    PayUseCase,
    VisitCarUseCase,
)
from src.application.robot_action.use_cases import (
    CreateRobotActionUseCase,
    ListRobotActionsUseCase,
    UpdateRobotActionUseCase,
)
from src.core.config import settings
from src.infrastructure.db.session import get_session
from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

# 주유 대기열(ready/waiting) 판단을 한 번에 하나씩만 하도록 막는 잠금. 프로세스 1개 기준.
_queue_lock = asyncio.Lock()


def now_local() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone)).replace(tzinfo=None, microsecond=0)


def get_visit_car_use_case(session: AsyncSession = Depends(get_session)) -> VisitCarUseCase:
    return VisitCarUseCase(
        SqlAlchemyUnitOfWork(session),
        clock=now_local,
        queue_lock=_queue_lock,
        done_window=timedelta(seconds=settings.done_redetect_window_seconds),
    )


def get_complete_fueling_use_case(session: AsyncSession = Depends(get_session)) -> CompleteFuelingUseCase:
    return CompleteFuelingUseCase(SqlAlchemyUnitOfWork(session), clock=now_local, queue_lock=_queue_lock)


def get_list_cars_use_case(session: AsyncSession = Depends(get_session)) -> ListCarsUseCase:
    return ListCarsUseCase(SqlAlchemyUnitOfWork(session))


def get_order_fuel_type_use_case(session: AsyncSession = Depends(get_session)) -> OrderFuelTypeUseCase:
    return OrderFuelTypeUseCase(SqlAlchemyUnitOfWork(session))


def get_pay_use_case(session: AsyncSession = Depends(get_session)) -> PayUseCase:
    return PayUseCase(SqlAlchemyUnitOfWork(session), clock=now_local, queue_lock=_queue_lock)


def get_robot_task_use_case(session: AsyncSession = Depends(get_session)) -> GetRobotTaskUseCase:
    return GetRobotTaskUseCase(SqlAlchemyUnitOfWork(session))


def get_create_robot_action_use_case(session: AsyncSession = Depends(get_session)) -> CreateRobotActionUseCase:
    return CreateRobotActionUseCase(SqlAlchemyUnitOfWork(session), clock=now_local)


def get_update_robot_action_use_case(session: AsyncSession = Depends(get_session)) -> UpdateRobotActionUseCase:
    return UpdateRobotActionUseCase(SqlAlchemyUnitOfWork(session), clock=now_local)


def get_list_robot_actions_use_case(session: AsyncSession = Depends(get_session)) -> ListRobotActionsUseCase:
    return ListRobotActionsUseCase(SqlAlchemyUnitOfWork(session))
