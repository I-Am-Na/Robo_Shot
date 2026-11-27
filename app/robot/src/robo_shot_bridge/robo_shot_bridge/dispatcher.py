"""polling 결과로 언제 주유를 시작할지 정하는 순수 로직 (ROS 의존 없음, 단위 테스트 대상).

규칙
- 한 번에 1대만 주유한다 (로봇 1대).
- 주유 중이거나 완료 보고가 남아 있으면 새 주유를 시작하지 않는다.
- 서버는 완료 보고 전까지 같은 차량을 계속 start=true로 내려주므로, 같은 차량을 두 번 시작하지 않는다.
- 주유에 실패한 차량은 자동으로 다시 시작하지 않는다 (사람이 확인 후 clear_failed).
"""

from robo_shot_bridge.server_client import RobotTask


class Dispatcher:
    def __init__(self) -> None:
        self.active_car: str | None = None  # 액션 전송~결과 수신 중인 차량
        self.pending_complete: str | None = None  # 주유는 끝났지만 서버에 완료 보고가 안 된 차량
        self.failed_cars: set[str] = set()

    @property
    def busy(self) -> bool:
        return self.active_car is not None or self.pending_complete is not None

    def next_goal(self, task: RobotTask) -> RobotTask | None:
        """이번 polling 결과로 주유를 시작해야 하면 task를, 아니면 None."""
        if self.busy or not task.start or not task.car_num:
            return None
        if task.car_num in self.failed_cars:
            return None
        if task.line_num not in (1, 2) or not task.fuel_type or not task.amount:
            return None
        return task

    def on_goal_sent(self, car_num: str) -> None:
        self.active_car = car_num

    def on_goal_rejected(self, car_num: str) -> None:
        """로봇이 거절(예: 이미 주유 중). 다음 polling에서 다시 시도한다."""
        if self.active_car == car_num:
            self.active_car = None

    def on_fueling_finished(self, car_num: str, success: bool) -> None:
        if self.active_car == car_num:
            self.active_car = None
        if success:
            self.pending_complete = car_num
        else:
            self.failed_cars.add(car_num)

    def on_complete_reported(self, car_num: str) -> None:
        if self.pending_complete == car_num:
            self.pending_complete = None

    def clear_failed(self, car_num: str) -> None:
        self.failed_cars.discard(car_num)
