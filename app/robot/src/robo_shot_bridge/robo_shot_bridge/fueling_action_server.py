"""Fueling 액션 서버 (주유 로봇 동작).

지금은 각 단계를 step_seconds만큼 기다리는 시뮬레이션이다.
TODO(규진): 아래 _step_* 함수 안을 두산 로봇팔 실제 동작으로 바꾼다.
            각 함수는 성공하면 그냥 return, 실패하면 FuelingStepError를 던지면 된다.

- 한 번에 1건만 수행한다. 주유 중에 들어온 goal은 거절한다.
- 취소 요청을 받으면 다음 단계로 넘어가기 전에 멈춘다.

파라미터
  action_name   (string, 기본 fueling)
  step_seconds  (double, 기본 1.0) 시뮬레이션 단계당 시간
"""

import threading
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from robo_shot_interfaces.action import Fueling

FUEL_TYPES = ("휘발유", "경유")


class FuelingStepError(Exception):
    pass


class FuelingActionServer(Node):
    def __init__(self) -> None:
        super().__init__("fueling_action_server")
        self.declare_parameter("action_name", "fueling")
        self.declare_parameter("step_seconds", 1.0)
        self._step_seconds = float(self.get_parameter("step_seconds").value)

        self._busy = threading.Lock()
        # README 시스템 흐름의 주유 시퀀스
        self._steps = [
            ("주유구 커버 개방", self._step_open_cover),
            ("주유캡 개방·거치", self._step_open_cap),
            ("노즐 파지", self._step_grip_nozzle),
            ("노즐 삽입", self._step_insert_nozzle),
            ("주유", self._step_fuel),
            ("노즐 회수·거치", self._step_return_nozzle),
            ("주유캡·커버 체결", self._step_close_cap_and_cover),
        ]

        self._server = ActionServer(
            self,
            Fueling,
            self.get_parameter("action_name").value,
            execute_callback=self._execute,
            goal_callback=self._on_goal,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=ReentrantCallbackGroup(),
        )
        self.get_logger().info("Fueling 액션 서버 준비 (시뮬레이션 모드)")

    # --- goal 접수 ---

    def _on_goal(self, goal: Fueling.Goal) -> GoalResponse:
        if self._busy.locked():
            self.get_logger().warn(f"주유 중이라 {goal.car_num} 요청을 거절합니다.")
            return GoalResponse.REJECT
        if goal.line_num not in (1, 2) or goal.fuel_type not in FUEL_TYPES or goal.amount <= 0:
            self.get_logger().error(f"잘못된 주유 요청을 거절합니다: {goal}")
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    # --- 실행 ---

    def _execute(self, goal_handle) -> Fueling.Result:
        goal = goal_handle.request
        result = Fueling.Result()
        if not self._busy.acquire(blocking=False):
            goal_handle.abort()
            result.success, result.message = False, "busy"
            return result
        try:
            self.get_logger().info(f"주유 시작: {goal.car_num} {goal.line_num}번 라인 {goal.fuel_type} {goal.amount}원")
            feedback = Fueling.Feedback()
            feedback.step_count = len(self._steps)
            for i, (name, step) in enumerate(self._steps, start=1):
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    result.success, result.message = False, f"canceled before '{name}'"
                    return result
                feedback.step, feedback.step_index = name, i
                goal_handle.publish_feedback(feedback)
                step(goal)

            goal_handle.succeed()
            result.success, result.message = True, "fueling completed"
            self.get_logger().info(f"주유 완료: {goal.car_num}")
            return result
        except FuelingStepError as e:
            goal_handle.abort()
            result.success, result.message = False, str(e)
            self.get_logger().error(f"주유 실패: {goal.car_num}: {e}")
            return result
        finally:
            self._busy.release()

    # --- 주유 단계 (TODO(규진): 실제 로봇 동작으로 교체) ---

    def _simulate(self, seconds: float | None = None) -> None:
        time.sleep(self._step_seconds if seconds is None else seconds)

    def _step_open_cover(self, goal: Fueling.Goal) -> None:
        self._simulate()

    def _step_open_cap(self, goal: Fueling.Goal) -> None:
        self._simulate()

    def _step_grip_nozzle(self, goal: Fueling.Goal) -> None:
        self._simulate()

    def _step_insert_nozzle(self, goal: Fueling.Goal) -> None:
        self._simulate()

    def _step_fuel(self, goal: Fueling.Goal) -> None:
        # 실제로는 goal.amount(원)만큼 주유. 시뮬레이션은 2단계 분량 시간.
        self._simulate(self._step_seconds * 2)

    def _step_return_nozzle(self, goal: Fueling.Goal) -> None:
        self._simulate()

    def _step_close_cap_and_cover(self, goal: Fueling.Goal) -> None:
        self._simulate()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FuelingActionServer()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
