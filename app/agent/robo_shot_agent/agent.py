"""Robo-Shot 주유 주문·복창 확인 AI Agent 핵심 엔진.

PRD v1.3 요구사항을 코드 레벨에서 강제한다:
1. 신규 방문: 유종 + 금액(또는 용량) 수집 → 복창 → '네/아니오' 확인
2. 재방문: DB 저장 유종으로 유종 질문 생략, 금액(또는 용량)만 발화 → 반드시 유종 포함 복창 → '네/아니오' 확인
3. 안전 규칙: 고객이 '네'로 승인한 시점에만 should_save_fuel_type=True, should_show_qr=True 반환
4. 용량(리터) 발화 시 주입받은 fuel_prices(향후 유가 오픈 API 연동)로 금액(원) 환산
"""

from __future__ import annotations

from collections.abc import Mapping

from robo_shot_agent.llm import LLMExtractor
from robo_shot_agent.schemas import (
    DEFAULT_FUEL_PRICES,
    MAX_ORDER_AMOUNT,
    MIN_ORDER_AMOUNT,
    AgentTurnResult,
    ConfirmedOrder,
    DialogTurn,
    FuelType,
    LLMExtraction,
    OrderDraft,
    SessionState,
)


def format_won(amount: int) -> str:
    return f"{amount:,}원"


def format_liters(liters: float) -> str:
    return f"{int(liters)}리터" if liters.is_integer() else f"{liters:g}리터"


class FuelingOrderAgent:
    """상태 기반 멀티턴 음성 주문 AI Agent."""

    def __init__(
        self,
        extractor: LLMExtractor,
        default_fuel_prices: Mapping[FuelType, int] | None = None,
        max_retries: int = 3,
        max_history_turns: int = 8,
    ) -> None:
        self._extractor = extractor
        self._default_prices: dict[FuelType, int] = dict(default_fuel_prices or DEFAULT_FUEL_PRICES)
        self._max_retries = max_retries
        self._max_history_turns = max_history_turns

    def initial_greeting(self, state: SessionState) -> str:
        """차량이 ready 상태가 되었을 때 TTS로 출력할 첫 안내 멘트."""
        if state.is_revisit:
            return "다시 방문해주셔서 감사합니다. 주유하실 금액이나 용량을 말씀해주세요."
        return "주유를 시작합니다. 유종과 금액 또는 용량을 말씀해주세요."

    def process_turn(
        self,
        state: SessionState,
        user_text: str,
        fuel_prices: Mapping[FuelType, int] | None = None,
    ) -> AgentTurnResult:
        """운전자 STT 발화 1턴을 처리하고 다음 TTS 문구·상태·액션 플래그를 반환한다."""
        next_state = state.model_copy(deep=True)
        prices = dict(fuel_prices) if fuel_prices is not None else self._default_prices
        cleaned = user_text.strip()

        if next_state.phase in ("confirmed", "canceled"):
            reply = (
                "이미 주문이 확정되었습니다. 화면의 QR 코드로 결제해주세요."
                if next_state.phase == "confirmed"
                else "이미 취소된 주문입니다."
            )
            return AgentTurnResult(
                reply_text=reply,
                intent="unclear",
                phase=next_state.phase,
                draft=next_state.draft,
                state=next_state,
            )

        if not cleaned:
            return self._handle_unclear(next_state, "말소리가 잘 들리지 않았습니다. 다시 말씀해주세요.")

        extraction = self._extractor.extract(self._build_prompt_inputs(next_state, cleaned))
        next_state.history.append(DialogTurn(role="user", text=cleaned))

        result = self._apply_transition(next_state, extraction, prices)
        result.state.history.append(DialogTurn(role="assistant", text=result.reply_text))
        if len(result.state.history) > self._max_history_turns * 2:
            result.state.history = result.state.history[-self._max_history_turns * 2 :]
        return result

    # --- 내부 상태 전이 로직 ---

    def _apply_transition(
        self,
        state: SessionState,
        ext: LLMExtraction,
        prices: Mapping[FuelType, int],
    ) -> AgentTurnResult:
        # 1) 어느 단계에서든 취소 요청 우선 처리
        if ext.intent == "cancel":
            state.phase = "canceled"
            state.retry_count = 0
            return AgentTurnResult(
                reply_text="주문을 취소했습니다. 이용해주셔서 감사합니다.",
                intent="cancel",
                phase="canceled",
                draft=state.draft,
                state=state,
            )

        # 2) 미지원 유종 안내
        if ext.intent == "unsupported":
            fuel_label = ext.unsupported_fuel or "말씀하신 유종"
            reply = f"{fuel_label}는 지원하지 않습니다. 휘발유 또는 경유로 말씀해주세요."
            return AgentTurnResult(
                reply_text=reply,
                intent="unsupported",
                phase=state.phase,
                draft=state.draft,
                state=state,
            )

        # 3) 복창 확인 대기(confirming) 단계 처리
        if state.phase == "confirming":
            if ext.intent == "confirm":
                return self._finalize_confirmed(state, prices)
            if ext.intent == "deny" and ext.fuel_type is None and ext.amount is None and ext.liters is None:
                # 거절 후 재주문 루프 복귀 (재방문 차량이라도 혼유 방지를 위해 유종을 비우고 다시 받을 수 있게 함)
                state.phase = "collecting"
                state.draft = OrderDraft()
                state.retry_count = 0
                return AgentTurnResult(
                    reply_text="알겠습니다. 유종과 금액 또는 용량을 다시 말씀해주세요.",
                    intent="deny",
                    phase="collecting",
                    draft=state.draft,
                    state=state,
                )
            if ext.intent in ("modify", "order", "deny"):
                return self._update_draft_and_respond(state, ext, prices)
            return self._handle_unclear(
                state,
                f"잘 이해하지 못했습니다. {self._build_confirmation_message(state.draft)}",
            )

        # 4) 정보 수집(collecting) 단계 처리
        if ext.intent in ("order", "modify"):
            return self._update_draft_and_respond(state, ext, prices)

        # collecting 단계에서 '네/아니오'나 불명확 발화가 온 경우
        return self._handle_unclear(state, ext.reply_hint or self._ask_missing_prompt(state))

    def _update_draft_and_respond(
        self,
        state: SessionState,
        ext: LLMExtraction,
        prices: Mapping[FuelType, int],
    ) -> AgentTurnResult:
        # 슬롯 병합: 새로 언급된 값만 덮어쓰고, 금액↔리터 상호 교체 시 이전 단위는 초기화
        if ext.fuel_type is not None:
            state.draft.fuel_type = ext.fuel_type
        elif state.draft.fuel_type is None and state.saved_fuel_type is not None:
            state.draft.fuel_type = state.saved_fuel_type

        if ext.amount is not None:
            if not (MIN_ORDER_AMOUNT <= ext.amount <= MAX_ORDER_AMOUNT):
                return AgentTurnResult(
                    reply_text="주문 가능한 금액 범위를 벗어났습니다. 금액을 다시 말씀해주세요.",
                    intent=ext.intent,
                    phase="collecting",
                    draft=state.draft,
                    state=state,
                )
            state.draft.amount = ext.amount
            state.draft.liters = None
        elif ext.liters is not None:
            if ext.liters <= 0:
                return AgentTurnResult(
                    reply_text="올바른 용량을 다시 말씀해주세요.",
                    intent=ext.intent,
                    phase="collecting",
                    draft=state.draft,
                    state=state,
                )
            state.draft.liters = ext.liters
            state.draft.amount = None

        # 용량(리터)이 있고 유종이 확정되었으면 유가 기준으로 원 단위 금액 환산
        if state.draft.liters is not None and state.draft.fuel_type is not None:
            unit_price = prices.get(state.draft.fuel_type, DEFAULT_FUEL_PRICES[state.draft.fuel_type])
            computed = round(state.draft.liters * unit_price)
            if not (MIN_ORDER_AMOUNT <= computed <= MAX_ORDER_AMOUNT):
                state.draft.liters = None
                return AgentTurnResult(
                    reply_text="계산된 금액이 주문 가능 범위를 벗어났습니다. 용량을 다시 말씀해주세요.",
                    intent=ext.intent,
                    phase="collecting",
                    draft=state.draft,
                    state=state,
                )
            state.draft.amount = computed

        # 필수 슬롯(유종 + 금액 또는 리터) 누락 시 누락 항목만 질문
        if state.draft.fuel_type is None or (state.draft.amount is None and state.draft.liters is None):
            state.phase = "collecting"
            state.retry_count = 0
            return AgentTurnResult(
                reply_text=self._ask_missing_prompt(state),
                intent=ext.intent,
                phase="collecting",
                draft=state.draft,
                state=state,
            )

        # 유종 + 금액(또는 용량 환산 금액) 모두 준비됨 → 복창 확인(confirming) 단계로 전이
        state.phase = "confirming"
        state.retry_count = 0
        return AgentTurnResult(
            reply_text=self._build_confirmation_message(state.draft),
            intent=ext.intent,
            phase="confirming",
            draft=state.draft,
            state=state,
        )

    def _finalize_confirmed(
        self,
        state: SessionState,
        prices: Mapping[FuelType, int],
    ) -> AgentTurnResult:
        fuel = state.draft.fuel_type
        amount = state.draft.amount
        if fuel is not None and amount is None and state.draft.liters is not None:
            unit_price = prices.get(fuel, DEFAULT_FUEL_PRICES[fuel])
            amount = round(state.draft.liters * unit_price)
            state.draft.amount = amount

        if fuel is None or amount is None or not (MIN_ORDER_AMOUNT <= amount <= MAX_ORDER_AMOUNT):
            state.phase = "collecting"
            return AgentTurnResult(
                reply_text=self._ask_missing_prompt(state),
                intent="unclear",
                phase="collecting",
                draft=state.draft,
                state=state,
            )

        state.phase = "confirmed"
        state.retry_count = 0
        confirmed = ConfirmedOrder(fuel_type=fuel, amount=amount, liters=state.draft.liters)
        return AgentTurnResult(
            reply_text="주문이 확인되었습니다. 화면의 QR 코드로 결제해주세요.",
            intent="confirm",
            phase="confirmed",
            draft=state.draft,
            confirmed_order=confirmed,
            should_save_fuel_type=True,
            should_show_qr=True,
            state=state,
        )

    def _handle_unclear(self, state: SessionState, fallback_reply: str) -> AgentTurnResult:
        state.retry_count += 1
        if state.retry_count >= self._max_retries:
            reply = "음성 인식이 여러 번 실패했습니다. 잠시 후 다시 말씀해주시거나 화면에서 입력해주세요."
        else:
            reply = fallback_reply
        return AgentTurnResult(
            reply_text=reply,
            intent="unclear",
            phase=state.phase,
            draft=state.draft,
            state=state,
        )

    def _ask_missing_prompt(self, state: SessionState) -> str:
        has_fuel = state.draft.fuel_type is not None
        has_qty = state.draft.amount is not None or state.draft.liters is not None
        if not has_fuel and not has_qty:
            return "유종과 주유하실 금액 또는 용량을 말씀해주세요."
        if not has_fuel:
            qty_text = (
                format_liters(state.draft.liters)
                if state.draft.liters is not None
                else format_won(state.draft.amount or 0)
            )
            return f"{qty_text} 확인했습니다. 휘발유와 경유 중 어떤 유종으로 넣어드릴까요?"
        return f"{state.draft.fuel_type} 확인했습니다. 주유하실 금액이나 용량을 말씀해주세요."

    def _build_confirmation_message(self, draft: OrderDraft) -> str:
        """PRD v1.3 안전 규칙: 재방문 차량도 번호판 오인식 방지를 위해 반드시 유종을 포함해 복창한다."""
        fuel = draft.fuel_type or ""
        if draft.liters is not None and draft.amount is not None:
            return f"{fuel} {format_liters(draft.liters)}, {format_won(draft.amount)} 주유하겠습니다. 맞으신가요?"
        if draft.amount is not None:
            return f"{fuel} {format_won(draft.amount)} 주유하겠습니다. 맞으신가요?"
        return f"{fuel} 주유하겠습니다. 맞으신가요?"

    def _build_prompt_inputs(self, state: SessionState, user_text: str) -> dict[str, str]:
        recent = state.history[-self._max_history_turns :]
        history_text = (
            "\n".join(f"{'운전자' if t.role == 'user' else '로보샷'}: {t.text}" for t in recent)
            if recent
            else "(없음)"
        )
        return {
            "car_num": state.car_num,
            "visit_type": "재방문 차량" if state.is_revisit else "신규 방문 차량",
            "saved_fuel_type": state.saved_fuel_type or "없음",
            "dialog_state": state.phase,
            "draft_fuel_type": state.draft.fuel_type or "미정",
            "draft_amount": format_won(state.draft.amount) if state.draft.amount else "미정",
            "draft_liters": format_liters(state.draft.liters) if state.draft.liters else "미정",
            "history": history_text,
            "user_input": user_text,
        }
