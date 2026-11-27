from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CarModel(Base):
    """차량 정보. car_num 당 1행."""

    __tablename__ = "car"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    car_num: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, comment="차량번호")
    is_line: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="라인 여부")
    line_num: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="라인 번호(1 또는 2)")
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
