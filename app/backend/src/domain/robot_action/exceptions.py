class RobotActionNotFoundError(Exception):
    def __init__(self, action_id: int):
        super().__init__(f"robot action not found: {action_id}")
        self.action_id = action_id


class InvalidRobotActionTransition(Exception):
    def __init__(self, action_id: int | None, current: str, requested: str):
        super().__init__(f"robot action {action_id}: cannot change status {current} -> {requested}")
        self.current = current
        self.requested = requested
