from dataclasses import dataclass
from datetime import datetime

from src.domain.robot_action.exceptions import InvalidRobotActionTransition

# status 값
REQUESTED = "requested"  # 중간 노드가 로봇에 goal을 보냄
RUNNING = "running"  # 로봇이 수락하고 주유 중
SUCCEEDED = "succeeded"  # 주유 완료
FAILED = "failed"  # 주유 실패
CANCELED = "canceled"  # 주유 취소
REJECTED = "rejected"  # 로봇이 goal을 거절 (예: 이미 주유 중)

TERMINAL_STATUSES = (SUCCEEDED, FAILED, CANCELED, REJECTED)
ALL_STATUSES = (REQUESTED, RUNNING, *TERMINAL_STATUSES)

_ALLOWED: dict[str, tuple[str, ...]] = {
    REQUESTED: (RUNNING, REJECTED, FAILED, CANCELED),
    RUNNING: (RUNNING, SUCCEEDED, FAILED, CANCELED),
}


@dataclass
class RobotAction:
    """로봇 주유 1건의 실행 기록. 상태 흐름:

        requested --수락--> running --(단계 진행: running 유지)--> succeeded | failed | canceled
        requested --거절--> rejected
    끝난 기록(succeeded/failed/canceled/rejected)은 바꿀 수 없다.
    """

    car_num: str
    line_num: int
    fuel_type: str
    amount: int
    created_at: datetime
    status: str = REQUESTED
    step: str | None = None
    step_index: int | None = None
    step_count: int | None = None
    message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    id: int | None = None

    @property
    def is_finished(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def apply(
        self,
        status: str,
        now: datetime,
        step: str | None = None,
        step_index: int | None = None,
        step_count: int | None = None,
        message: str | None = None,
    ) -> None:
        if status not in _ALLOWED.get(self.status, ()):
            raise InvalidRobotActionTransition(self.id, self.status, status)

        if status == RUNNING and self.started_at is None:
            self.started_at = now
        if status in TERMINAL_STATUSES:
            self.finished_at = now
        if step is not None:
            self.step = step
        if step_index is not None:
            self.step_index = step_index
        if step_count is not None:
            self.step_count = step_count
        if message is not None:
            self.message = message
        self.status = status
