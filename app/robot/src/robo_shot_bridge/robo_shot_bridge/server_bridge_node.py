"""중간 연결 노드: 서버 polling → Fueling 액션 전송 → 완료 보고.

흐름
  1. poll_interval마다 GET /robot/task
  2. start=true 이고 지금 주유 중이 아니면 Fueling 액션 goal 전송 (같은 차량은 한 번만)
  3. 결과 success=true → PUT /car/{car_num}/complete (실패하면 다음 polling 때 다시 보고)
     결과 실패 → 그 차량은 자동으로 다시 시작하지 않음 (로그 확인 필요)
  4. 실행 기록(robot_action): goal 전송 시 POST /robot/actions, 수락·단계·결과 때 PUT /robot/actions/{id}
     기록 실패는 로그만 남기고 주유는 계속한다.

파라미터
  server_url     (string, 기본 http://localhost:8000)
  poll_interval  (double, 초, 기본 2.0)
  action_name    (string, 기본 fueling)
"""

import rclpy
from action_msgs.msg import GoalStatus
from rclpy.action import ActionClient
from rclpy.node import Node

from robo_shot_bridge.dispatcher import Dispatcher
from robo_shot_bridge.server_client import RobotTask, ServerClient, ServerError
from robo_shot_interfaces.action import Fueling


class ServerBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__("server_bridge")
        self.declare_parameter("server_url", "http://localhost:8000")
        self.declare_parameter("poll_interval", 2.0)
        self.declare_parameter("action_name", "fueling")

        server_url = self.get_parameter("server_url").value
        poll_interval = float(self.get_parameter("poll_interval").value)
        action_name = self.get_parameter("action_name").value

        self._server = ServerClient(server_url)
        self._dispatcher = Dispatcher()
        self._action_ids: dict[str, int] = {}  # car_num -> robot_action id (진행 중인 기록)
        self._action = ActionClient(self, Fueling, action_name)
        self._timer = self.create_timer(poll_interval, self._poll)
        self.get_logger().info(f"polling {server_url}/robot/task every {poll_interval}s, action='{action_name}'")

    # --- polling ---

    def _poll(self) -> None:
        if self._dispatcher.pending_complete:
            self._report_complete(self._dispatcher.pending_complete)
            return
        if self._dispatcher.busy:
            return

        try:
            task = self._server.get_task()
        except ServerError as e:
            self.get_logger().warn(str(e), throttle_duration_sec=10.0)
            return

        if task.start and task.car_num in self._dispatcher.failed_cars:
            self.get_logger().error(
                f"{task.car_num} 은(는) 주유에 실패한 차량이라 자동으로 다시 시작하지 않습니다.",
                throttle_duration_sec=30.0,
            )
        goal = self._dispatcher.next_goal(task)
        if goal is None:
            return

        if not self._action.server_is_ready():
            self.get_logger().warn("Fueling 액션 서버가 아직 없습니다. 다음 polling에서 다시 시도합니다.",
                                   throttle_duration_sec=10.0)
            return
        self._send_goal(goal)

    # --- 액션 ---

    def _send_goal(self, task: RobotTask) -> None:
        msg = Fueling.Goal()
        msg.car_num = task.car_num
        msg.line_num = int(task.line_num)
        msg.fuel_type = task.fuel_type
        msg.amount = int(task.amount)

        car_num = task.car_num
        self._dispatcher.on_goal_sent(car_num)
        self._record_start(task)
        self.get_logger().info(f"주유 시작 요청: {car_num} {task.line_num}번 라인 {task.fuel_type} {task.amount}원")
        future = self._action.send_goal_async(msg, feedback_callback=self._on_feedback)
        future.add_done_callback(lambda f: self._on_goal_response(car_num, f))

    def _on_goal_response(self, car_num: str, future) -> None:
        handle = future.result()
        if not handle.accepted:
            self.get_logger().warn(f"로봇이 {car_num} 주유 요청을 거절했습니다. 다음 polling에서 다시 시도합니다.")
            self._dispatcher.on_goal_rejected(car_num)
            self._record(car_num, "rejected", finished=True, message="goal rejected by robot")
            return
        self._record(car_num, "running")
        handle.get_result_async().add_done_callback(lambda f: self._on_result(car_num, f))

    def _on_feedback(self, feedback_msg) -> None:
        fb = feedback_msg.feedback
        self.get_logger().info(f"  [{fb.step_index}/{fb.step_count}] {fb.step}")
        car_num = self._dispatcher.active_car
        if car_num:
            self._record(car_num, "running", step=fb.step, step_index=int(fb.step_index),
                         step_count=int(fb.step_count))

    def _on_result(self, car_num: str, future) -> None:
        wrapped = future.result()
        success = wrapped.status == GoalStatus.STATUS_SUCCEEDED and wrapped.result.success
        self._dispatcher.on_fueling_finished(car_num, success)
        if success:
            self._record(car_num, "succeeded", finished=True, message=wrapped.result.message or None)
        elif wrapped.status == GoalStatus.STATUS_CANCELED:
            self._record(car_num, "canceled", finished=True, message=wrapped.result.message or None)
        else:
            self._record(car_num, "failed", finished=True, message=wrapped.result.message or f"status={wrapped.status}")
        if success:
            self.get_logger().info(f"주유 완료: {car_num}")
            self._report_complete(car_num)
        else:
            self.get_logger().error(
                f"주유 실패: {car_num} (status={wrapped.status}, message={wrapped.result.message}). "
                "서버에는 완료 보고하지 않습니다."
            )

    # --- 실행 기록 (best-effort) ---

    def _record_start(self, task: RobotTask) -> None:
        try:
            self._action_ids[task.car_num] = self._server.create_action(task)
        except ServerError as e:
            self.get_logger().warn(f"실행 기록 생성 실패 (주유는 계속): {e}")

    def _record(self, car_num: str, status: str, finished: bool = False, **fields) -> None:
        action_id = self._action_ids.get(car_num)
        if action_id is None:
            return
        try:
            self._server.update_action(action_id, status, **fields)
        except ServerError as e:
            self.get_logger().warn(f"실행 기록 갱신 실패 ({status}): {e}", throttle_duration_sec=5.0)
        if finished:
            self._action_ids.pop(car_num, None)

    # --- 완료 보고 ---

    def _report_complete(self, car_num: str) -> None:
        try:
            next_car = self._server.complete(car_num)
        except ServerError as e:
            self.get_logger().warn(f"완료 보고 실패, 다시 시도합니다: {e}", throttle_duration_sec=10.0)
            return
        self._dispatcher.on_complete_reported(car_num)
        self.get_logger().info(f"서버에 완료 보고: {car_num} → 다음 차량: {next_car or '없음'}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ServerBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
