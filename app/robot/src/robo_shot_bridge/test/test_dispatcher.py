from robo_shot_bridge.dispatcher import Dispatcher
from robo_shot_bridge.server_client import RobotTask

PAID = RobotTask(start=True, car_num="11가1111", line_num=1, fuel_type="휘발유", amount=50000)
NO_TASK = RobotTask(start=False)


def test_starts_when_paid_car_and_idle():
    d = Dispatcher()
    assert d.next_goal(NO_TASK) is None
    assert d.next_goal(PAID) == PAID


def test_does_not_start_same_car_twice_while_fueling():
    d = Dispatcher()
    d.on_goal_sent(PAID.car_num)
    assert d.next_goal(PAID) is None  # 서버는 완료 전까지 같은 차를 계속 내려준다


def test_waits_for_complete_report_before_next_goal():
    d = Dispatcher()
    d.on_goal_sent(PAID.car_num)
    d.on_fueling_finished(PAID.car_num, success=True)
    assert d.pending_complete == PAID.car_num
    other = RobotTask(start=True, car_num="22나2222", line_num=2, fuel_type="경유", amount=30000)
    assert d.next_goal(other) is None
    d.on_complete_reported(PAID.car_num)
    assert d.next_goal(other) == other


def test_rejected_goal_is_retried_next_poll():
    d = Dispatcher()
    d.on_goal_sent(PAID.car_num)
    d.on_goal_rejected(PAID.car_num)
    assert d.next_goal(PAID) == PAID


def test_failed_car_is_not_restarted_automatically():
    d = Dispatcher()
    d.on_goal_sent(PAID.car_num)
    d.on_fueling_finished(PAID.car_num, success=False)
    assert d.pending_complete is None
    assert d.next_goal(PAID) is None
    d.clear_failed(PAID.car_num)
    assert d.next_goal(PAID) == PAID


def test_invalid_task_is_ignored():
    d = Dispatcher()
    assert d.next_goal(RobotTask(start=True, car_num="11가1111", line_num=3, fuel_type="휘발유", amount=1)) is None
    assert d.next_goal(RobotTask(start=True, car_num="11가1111", line_num=1, fuel_type="휘발유", amount=0)) is None
