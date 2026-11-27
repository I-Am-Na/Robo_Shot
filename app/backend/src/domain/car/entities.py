from dataclasses import dataclass
from datetime import datetime, timedelta

from src.domain.car.exceptions import CarNotReadyError
from src.domain.car.value_objects import (
    QUEUE_STATUSES,
    STATUS_DONE,
    STATUS_PAID,
    STATUS_READY,
    STATUS_WAITING,
    FuelType,
)


@dataclass
class Car:
    """차량 Aggregate Root. car_num 당 1건을 유지한다.

    status 흐름 (주유 로봇 1대, 라인 2개):
        (없음/done) --라인 정상 진입--> ready   : 로봇을 차지한(ready/paid) 차량이 없을 때
                                    \\-> waiting : 이미 ready/paid 차량이 있을 때
        ready   --QR 결제 완료--> paid   : 로봇이 polling으로 받아 주유 시작
        paid    --주유 완료--> done
        waiting --앞 차량 완료--> ready (먼저 기다린 차량부터)
    """

    car_num: str
    is_line: bool
    line_num: int
    updated_at: datetime
    fuel_type: FuelType | None = None
    status: str | None = None
    status_updated_at: datetime | None = None
    id: int | None = None

    @classmethod
    def register(
        cls,
        car_num: str,
        is_line: bool,
        line_num: int,
        detected_at: datetime,
        fuel_type: FuelType | None = None,
    ) -> "Car":
        """처음 감지된 차량을 만든다. 상태는 enter_queue에서 정한다."""
        return cls(
            car_num=car_num, is_line=is_line, line_num=line_num, updated_at=detected_at, fuel_type=fuel_type
        )

    def update(
        self,
        is_line: bool,
        line_num: int,
        updated_at: datetime,
        fuel_type: FuelType | None = None,
    ) -> None:
        self.is_line = is_line
        self.line_num = line_num
        self.updated_at = updated_at
        # 유종은 확인된 값이 들어왔을 때만 갱신한다. 없으면 저장된 값을 유지한다.
        if fuel_type is not None:
            self.fuel_type = fuel_type

    # --- 대기열 ---

    @property
    def is_in_queue(self) -> bool:
        return self.status in QUEUE_STATUSES

    def should_enter_queue(self, now: datetime, done_window: timedelta) -> bool:
        """라인에 정상 진입했고, 아직 대기열에 없고, 방금 주유를 끝낸 차량이 아니면 대기열에 넣는다.

        주유를 끝낸 차량이 빠져나가는 동안 YOLO가 계속 감지해도 다시 줄을 서지 않게
        done 후 done_window 동안은 넣지 않는다.
        """
        if not self.is_line or self.is_in_queue:
            return False
        if self.status == STATUS_DONE and self.status_updated_at is not None:
            return now - self.status_updated_at >= done_window
        return True

    def enter_queue(self, robot_busy: bool, now: datetime) -> None:
        self._set_status(STATUS_WAITING if robot_busy else STATUS_READY, now)

    def complete_fueling(self, now: datetime) -> None:
        """주유 완료. 보통 paid 차량이지만, 테스트·취소를 위해 결제 전(ready) 차량도 허용한다."""
        if self.status not in (STATUS_READY, STATUS_PAID):
            raise CarNotReadyError(self.car_num, self.status)
        self._set_status(STATUS_DONE, now)

    def pay(self, fuel_type: FuelType, now: datetime) -> None:
        """QR 결제 완료. 주유 준비(ready) 차량만 결제할 수 있다."""
        if self.status != STATUS_READY:
            raise CarNotReadyError(self.car_num, self.status)
        self.fuel_type = fuel_type
        self._set_status(STATUS_PAID, now)

    def order_fuel_type(self, fuel_type: FuelType) -> None:
        """고객이 음성으로 주문한 유종을 저장한다. 주유 준비(ready) 차량만 주문할 수 있다."""
        if self.status != STATUS_READY:
            raise CarNotReadyError(self.car_num, self.status)
        self.fuel_type = fuel_type

    def promote(self, now: datetime) -> None:
        """대기 중인 차량을 주유 준비 상태로 올린다."""
        self._set_status(STATUS_READY, now)

    def _set_status(self, status: str, now: datetime) -> None:
        self.status = status
        self.status_updated_at = now
