from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.domain.car.value_objects import FuelType


class Base(DeclarativeBase):
    pass


class CarModel(Base):
    """차량 정보. car_num 당 1행."""

    __tablename__ = "car"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    car_num: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, comment="차량번호")
    is_line: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="라인 여부")
    line_num: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="라인 번호(1 또는 2)")
    fuel_type: Mapped[FuelType | None] = mapped_column(
        Enum(FuelType, name="fuel_type", values_callable=lambda e: [m.value for m in e]),
        nullable=True,
        comment="유종(휘발유/경유). 신규 차량은 NULL",
    )
    status: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True, comment="차량 상태(ready/waiting/done)"
    )
    status_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="상태 변경 일시. 대기 순서 기준"
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="최종 갱신 일시")


class PaymentModel(Base):
    """차량 방문기록. 방문마다 1행."""

    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    car_num: Mapped[str] = mapped_column(
        String(20), ForeignKey("car.car_num"), nullable=False, index=True, comment="차량번호"
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="금액")
    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="방문 일시")


class RobotActionModel(Base):
    """로봇 주유 실행 기록. 주유 1건 = 1행."""

    __tablename__ = "robot_action"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    car_num: Mapped[str] = mapped_column(
        String(20), ForeignKey("car.car_num"), nullable=False, index=True, comment="차량번호"
    )
    line_num: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="주유 라인(1 또는 2)")
    fuel_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="유종")
    amount: Mapped[int] = mapped_column(Integer, nullable=False, comment="결제 금액(원)")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        comment="requested | running | succeeded | failed | canceled | rejected",
    )
    step: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="현재(마지막) 단계")
    step_index: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="단계 번호(1부터)")
    step_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="전체 단계 수")
    message: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="결과 메시지·실패 이유")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="goal 전송 일시")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="로봇 수락(주유 시작) 일시")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="종료 일시")
