from sqlalchemy.ext.asyncio import AsyncSession

from src.application.unit_of_work import UnitOfWork
from src.infrastructure.db.repositories import (
    SqlAlchemyCarRepository,
    SqlAlchemyPaymentRepository,
    SqlAlchemyRobotActionRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession):
        self._session = session
        self.cars = SqlAlchemyCarRepository(session)
        self.payments = SqlAlchemyPaymentRepository(session)
        self.robot_actions = SqlAlchemyRobotActionRepository(session)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
