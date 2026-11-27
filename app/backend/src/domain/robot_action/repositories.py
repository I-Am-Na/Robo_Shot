from abc import ABC, abstractmethod

from src.domain.robot_action.entities import RobotAction


class RobotActionRepository(ABC):
    @abstractmethod
    async def add(self, action: RobotAction) -> RobotAction: ...

    @abstractmethod
    async def get(self, action_id: int) -> RobotAction | None: ...

    @abstractmethod
    async def save(self, action: RobotAction) -> RobotAction: ...

    @abstractmethod
    async def list_recent(self, limit: int, car_num: str | None = None) -> list[RobotAction]:
        """최근 생성된 순서로."""
