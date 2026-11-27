from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.car.entities import Car
from src.domain.car.repositories import CarRepository
from src.domain.payment.entities import Payment
from src.domain.payment.repositories import PaymentRepository
from src.domain.robot_action.entities import RobotAction
from src.domain.robot_action.repositories import RobotActionRepository
from src.infrastructure.db.models import CarModel, PaymentModel, RobotActionModel


def _to_entity(row: CarModel) -> Car:
    return Car(
        id=row.id,
        car_num=row.car_num,
        is_line=row.is_line,
        line_num=row.line_num,
        updated_at=row.updated_at,
        fuel_type=row.fuel_type,
        status=row.status,
        status_updated_at=row.status_updated_at,
    )


class SqlAlchemyCarRepository(CarRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_car_num(self, car_num: str) -> Car | None:
        row = await self._session.scalar(select(CarModel).where(CarModel.car_num == car_num))
        return _to_entity(row) if row is not None else None

    async def save(self, car: Car) -> Car:
        if car.id is None:
            row = CarModel(car_num=car.car_num)
            self._session.add(row)
        else:
            row = await self._session.get(CarModel, car.id)
        row.is_line = car.is_line
        row.line_num = car.line_num
        row.updated_at = car.updated_at
        row.fuel_type = car.fuel_type
        row.status = car.status
        row.status_updated_at = car.status_updated_at
        await self._session.flush()
        car.id = row.id
        return car

    async def list_recent(self, limit: int) -> list[Car]:
        rows = await self._session.scalars(
            select(CarModel).order_by(CarModel.updated_at.desc(), CarModel.id.desc()).limit(limit)
        )
        return [_to_entity(row) for row in rows]

    async def list_by_status(self, status: str) -> list[Car]:
        rows = await self._session.scalars(
            select(CarModel)
            .where(CarModel.status == status)
            .order_by(CarModel.status_updated_at.asc(), CarModel.id.asc())
        )
        return [_to_entity(row) for row in rows]


class SqlAlchemyPaymentRepository(PaymentRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, payment: Payment) -> Payment:
        row = PaymentModel(car_num=payment.car_num, amount=payment.amount, paid_at=payment.paid_at)
        self._session.add(row)
        await self._session.flush()
        payment.id = row.id
        return payment

    async def find_latest_by_car_num(self, car_num: str) -> Payment | None:
        row = await self._session.scalar(
            select(PaymentModel)
            .where(PaymentModel.car_num == car_num)
            .order_by(PaymentModel.paid_at.desc(), PaymentModel.id.desc())
            .limit(1)
        )
        if row is None:
            return None
        return Payment(id=row.id, car_num=row.car_num, amount=row.amount, paid_at=row.paid_at)

    async def save(self, payment: Payment) -> Payment:
        row = await self._session.get(PaymentModel, payment.id)
        row.amount = payment.amount
        row.paid_at = payment.paid_at
        await self._session.flush()
        return payment


def _to_action(row: RobotActionModel) -> RobotAction:
    return RobotAction(
        id=row.id,
        car_num=row.car_num,
        line_num=row.line_num,
        fuel_type=row.fuel_type,
        amount=row.amount,
        status=row.status,
        step=row.step,
        step_index=row.step_index,
        step_count=row.step_count,
        message=row.message,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


_ACTION_FIELDS = (
    "car_num", "line_num", "fuel_type", "amount", "status", "step", "step_index", "step_count",
    "message", "created_at", "started_at", "finished_at",
)


class SqlAlchemyRobotActionRepository(RobotActionRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, action: RobotAction) -> RobotAction:
        row = RobotActionModel(**{f: getattr(action, f) for f in _ACTION_FIELDS})
        self._session.add(row)
        await self._session.flush()
        action.id = row.id
        return action

    async def get(self, action_id: int) -> RobotAction | None:
        row = await self._session.get(RobotActionModel, action_id)
        return _to_action(row) if row is not None else None

    async def save(self, action: RobotAction) -> RobotAction:
        row = await self._session.get(RobotActionModel, action.id)
        for f in _ACTION_FIELDS:
            setattr(row, f, getattr(action, f))
        await self._session.flush()
        return action

    async def list_recent(self, limit: int, car_num: str | None = None) -> list[RobotAction]:
        stmt = select(RobotActionModel)
        if car_num:
            stmt = stmt.where(RobotActionModel.car_num == car_num)
        rows = await self._session.scalars(stmt.order_by(RobotActionModel.id.desc()).limit(limit))
        return [_to_action(row) for row in rows]
