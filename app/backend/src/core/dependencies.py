from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.car.use_cases import VisitCarUseCase
from src.core.config import settings
from src.infrastructure.db.session import get_session
from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def now_local() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone)).replace(tzinfo=None, microsecond=0)


def get_visit_car_use_case(session: AsyncSession = Depends(get_session)) -> VisitCarUseCase:
    return VisitCarUseCase(SqlAlchemyUnitOfWork(session), clock=now_local)
