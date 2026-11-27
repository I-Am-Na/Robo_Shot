class CarNotFoundError(Exception):
    def __init__(self, car_num: str):
        super().__init__(f"car not found: {car_num}")
        self.car_num = car_num


class CarNotReadyError(Exception):
    """주유 준비(ready) 상태가 아닌 차량을 주유 완료 처리하려 할 때."""

    def __init__(self, car_num: str, status: str | None):
        super().__init__(f"car is not ready: {car_num} (status={status})")
        self.car_num = car_num
        self.status = status
