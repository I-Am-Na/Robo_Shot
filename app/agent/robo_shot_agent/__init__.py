"""Robo-Shot AI Agent 패키지.

백엔드(FastAPI)·프론트엔드·DB에 직접 의존하지 않는 순수 Python 패키지로,
추후 `app/backend` 내부 통합 또는 별도 `app/agent` 서버로 바로 이식할 수 있다.
"""

from robo_shot_agent.agent import FuelingOrderAgent
from robo_shot_agent.llm import LLMExtractor, OpenAIOrderExtractor
from robo_shot_agent.schemas import (
    AgentTurnResult,
    ConfirmedOrder,
    DialogPhase,
    DialogTurn,
    FuelType,
    IntentType,
    LLMExtraction,
    OrderDraft,
    SessionState,
)

__all__ = [
    "AgentTurnResult",
    "ConfirmedOrder",
    "DialogPhase",
    "DialogTurn",
    "FuelType",
    "FuelingOrderAgent",
    "IntentType",
    "LLMExtraction",
    "LLMExtractor",
    "OpenAIOrderExtractor",
    "OrderDraft",
    "SessionState",
]
