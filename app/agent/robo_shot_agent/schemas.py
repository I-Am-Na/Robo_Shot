"""입출력 Pydantic 스키마.

백엔드(`app/backend/src/domain/car/value_objects.py`, `schemas.py`) 및
프론트엔드(`app/frontend/src/types/api.ts`) 규격과 1:1 호환되도록 맞춘다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# 백엔드 FuelType Enum 값과 동일
FuelType = Literal["휘발유", "경유"]

# 대화 단계 (프론트엔드 OrderPhase와 매핑)
# - collecting : 유종/금액(또는 용량) 수집 중
# - confirming : 복창 완료, 고객의 "네/아니오" 승인 대기
# - confirmed  : 고객 "네" 승인 완료 → 유종 저장 & 결제 QR 표시
# - canceled   : 주문 취소
DialogPhase = Literal["collecting", "confirming", "confirmed", "canceled"]

# 사용자 발화 의도
IntentType = Literal[
    "order",        # 주문 정보 발화 (유종, 금액, 리터)
    "modify",       # 기존 주문 정정 ("휘발유 말고 경유", "3만원으로 바꿔줘")
    "confirm",      # 복창 내용 승인 ("네", "맞아요", "진행해주세요")
    "deny",         # 복창 내용 거절 ("아니오", "틀렸어요", "다시 할게요")
    "cancel",       # 주문 취소 ("취소할게요", "안 넣을게요")
    "unsupported",  # 지원하지 않는 유종/요청 (고급유, LPG 등)
    "unclear",      # 주유 주문과 무관하거나 알아듣기 어려운 발화
]

# 백엔드 PayRequest(schemas.py) 기준 금액 범위
MIN_ORDER_AMOUNT = 1
MAX_ORDER_AMOUNT = 10_000_000

DEFAULT_FUEL_PRICES: dict[FuelType, int] = {
    "휘발유": 1650,
    "경유": 1520,
}


class DialogTurn(BaseModel):
    """대화 이력 1턴."""

    role: Literal["user", "assistant"]
    text: str


class OrderDraft(BaseModel):
    """확정 전 수집 중인 주문 정보."""

    fuel_type: FuelType | None = None
    amount: int | None = Field(default=None, description="결제 금액(원)")
    liters: float | None = Field(default=None, description="요청 용량(리터)")


class ConfirmedOrder(BaseModel):
    """고객 '네' 승인 후 확정된 주문. 백엔드 PUT /car/{car_num}/fuel-type 및 결제 QR에 전달."""

    fuel_type: FuelType
    amount: int = Field(..., ge=MIN_ORDER_AMOUNT, le=MAX_ORDER_AMOUNT, description="결제 금액(원)")
    liters: float | None = Field(default=None, gt=0, description="용량 발화였을 경우 리터 값")


class SessionState(BaseModel):
    """차량 1건의 음성 주문 대화 상태 (JSON 직렬화 가능)."""

    car_num: str = Field(..., min_length=1, max_length=20)
    saved_fuel_type: FuelType | None = Field(
        default=None,
        description="DB에 저장된 기존 유종. 값이 있으면 재방문 차량으로 간주한다.",
    )
    phase: DialogPhase = "collecting"
    draft: OrderDraft = Field(default_factory=OrderDraft)
    history: list[DialogTurn] = Field(default_factory=list)
    retry_count: int = 0

    @property
    def is_revisit(self) -> bool:
        return self.saved_fuel_type is not None

    @classmethod
    def start(cls, car_num: str, saved_fuel_type: FuelType | None = None) -> SessionState:
        """ready 차량 진입 시 새 대화 세션을 생성한다."""
        return cls(
            car_num=car_num,
            saved_fuel_type=saved_fuel_type,
            phase="collecting",
            draft=OrderDraft(fuel_type=saved_fuel_type),
        )


class LLMExtraction(BaseModel):
    """GPT-4o Structured Output 스키마.

    LLM은 자연어 의도/슬롯 추출과 자연스러운 한국어 멘트 후보를 반환하고,
    최종 상태 전이와 안전 규칙(확정 전 DB 미저장, 복창 필수 등)은 Agent 코드가 강제한다.
    """

    intent: IntentType = Field(..., description="사용자 발화의 핵심 의도")
    fuel_type: FuelType | None = Field(
        default=None,
        description="발화에서 새롭게 언급되거나 정정된 유종. 언급이 없으면 null.",
    )
    amount: int | None = Field(
        default=None,
        description="발화에서 추출한 원 단위 금액(예: '5만원' -> 50000, '삼만 오천원' -> 35000). 언급이 없으면 null.",
    )
    liters: float | None = Field(
        default=None,
        description="발화에서 추출한 용량(리터)(예: '20리터' -> 20.0). 언급이 없으면 null.",
    )
    unsupported_fuel: str | None = Field(
        default=None,
        description="지원하지 않는 유종을 말한 경우 그 명칭(예: '고급유', 'LPG'). 없으면 null.",
    )
    reply_hint: str | None = Field(
        default=None,
        description="TTS로 읽어줄 짧고 정중한 한국어 안내 문구(1~2문장).",
    )


class AgentTurnResult(BaseModel):
    """외부(FastAPI 라우터, 프론트엔드, CLI)로 반환하는 1턴 처리 결과."""

    reply_text: str = Field(..., description="MSI 스피커(TTS)로 출력할 안내/복창 문구")
    intent: IntentType
    phase: DialogPhase
    draft: OrderDraft
    confirmed_order: ConfirmedOrder | None = None
    should_save_fuel_type: bool = Field(
        default=False,
        description="True일 때만 백엔드 PUT /car/{car_num}/fuel-type 으로 유종을 저장한다.",
    )
    should_show_qr: bool = Field(
        default=False,
        description="True일 때 프론트엔드에 결제 QR 코드를 표시한다.",
    )
    state: SessionState = Field(..., description="갱신된 대화 상태 (다음 턴에 그대로 전달)")
