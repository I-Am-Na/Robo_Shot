from enum import Enum

# car.status 값. 컬럼은 자유 문자열이며, 지금 정해진 값은 아래와 같다.
# 주유 로봇은 1대이므로 ready/paid 차량은 항상 최대 1대다.
STATUS_READY = "ready"  # 주유 준비. 음성 주문·결제를 받는 중
STATUS_PAID = "paid"  # 결제 완료. 로봇이 polling으로 받아 주유를 시작한다
STATUS_WAITING = "waiting"  # 앞 차량 주유가 끝나길 기다리는 중
STATUS_DONE = "done"  # 주유 완료

# 로봇을 차지하고 있는 상태 (이 상태 차량이 있으면 새 차량은 waiting)
BUSY_STATUSES = (STATUS_READY, STATUS_PAID)
# 대기열에 들어와 있는 상태 (재감지돼도 상태를 바꾸지 않음)
QUEUE_STATUSES = (STATUS_READY, STATUS_PAID, STATUS_WAITING)


class FuelType(str, Enum):
    GASOLINE = "휘발유"
    DIESEL = "경유"
