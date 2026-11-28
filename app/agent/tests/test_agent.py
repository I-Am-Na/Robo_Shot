"""FuelingOrderAgent 단위 테스트 (Mock LLM 기반, API 키 불필요)."""

from __future__ import annotations

from typing import Any

from robo_shot_agent import (
    FuelingOrderAgent,
    LLMExtraction,
    SessionState,
)


class FakeExtractor:
    """사전에 지정한 LLMExtraction 시퀀스를 순서대로 반환하는 테스트용 추출기."""

    def __init__(self, responses: list[LLMExtraction]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def extract(self, prompt_inputs: dict[str, Any]) -> LLMExtraction:
        self.calls.append(prompt_inputs)
        return self._responses.pop(0)


def test_new_car_single_turn_order_requires_confirmation_before_save():
    extractor = FakeExtractor(
        [
            LLMExtraction(intent="order", fuel_type="휘발유", amount=50000),
            LLMExtraction(intent="confirm"),
        ]
    )
    agent = FuelingOrderAgent(extractor=extractor)
    state = SessionState.start(car_num="12가3456", saved_fuel_type=None)

    assert "유종" in agent.initial_greeting(state)

    # 1턴: 주문 발화 -> 복창 확인 대기 (아직 저장/QR 금지)
    r1 = agent.process_turn(state, "휘발유 5만원 넣어주세요")
    assert r1.phase == "confirming"
    assert r1.should_save_fuel_type is False
    assert r1.should_show_qr is False
    assert r1.confirmed_order is None
    assert "휘발유" in r1.reply_text and "50,000원" in r1.reply_text

    # 2턴: '네' 승인 -> 유종 저장 & QR 표시
    r2 = agent.process_turn(r1.state, "네 맞아요")
    assert r2.phase == "confirmed"
    assert r2.should_save_fuel_type is True
    assert r2.should_show_qr is True
    assert r2.confirmed_order is not None
    assert r2.confirmed_order.fuel_type == "휘발유"
    assert r2.confirmed_order.amount == 50000


def test_new_car_multiturn_slot_filling():
    extractor = FakeExtractor(
        [
            LLMExtraction(intent="order", fuel_type="경유"),
            LLMExtraction(intent="order", amount=30000),
            LLMExtraction(intent="confirm"),
        ]
    )
    agent = FuelingOrderAgent(extractor=extractor)
    state = SessionState.start(car_num="34나5678")

    r1 = agent.process_turn(state, "경유요")
    assert r1.phase == "collecting"
    assert r1.draft.fuel_type == "경유"
    assert "금액" in r1.reply_text or "용량" in r1.reply_text

    r2 = agent.process_turn(r1.state, "3만원 넣어주세요")
    assert r2.phase == "confirming"
    assert "경유" in r2.reply_text and "30,000원" in r2.reply_text

    r3 = agent.process_turn(r2.state, "네")
    assert r3.phase == "confirmed"
    assert r3.confirmed_order is not None
    assert r3.confirmed_order.fuel_type == "경유"
    assert r3.confirmed_order.amount == 30000


def test_revisit_car_skips_fuel_question_but_includes_fuel_in_confirmation():
    extractor = FakeExtractor(
        [
            LLMExtraction(intent="order", amount=50000),
            LLMExtraction(intent="confirm"),
        ]
    )
    agent = FuelingOrderAgent(extractor=extractor)
    state = SessionState.start(car_num="11가1111", saved_fuel_type="휘발유")

    # 재방문 첫 인사는 유종 질문 생략
    greeting = agent.initial_greeting(state)
    assert "유종" not in greeting
    assert "금액" in greeting

    # 금액만 발화해도 저장된 휘발유를 포함해 복창
    r1 = agent.process_turn(state, "5만원 넣어주세요")
    assert r1.phase == "confirming"
    assert "휘발유" in r1.reply_text and "50,000원" in r1.reply_text
    assert r1.should_save_fuel_type is False

    r2 = agent.process_turn(r1.state, "네")
    assert r2.phase == "confirmed"
    assert r2.confirmed_order is not None
    assert r2.confirmed_order.fuel_type == "휘발유"
    assert r2.confirmed_order.amount == 50000


def test_revisit_car_corrects_fuel_type_on_misrecognition():
    """번호판 오인식으로 잘못된 유종(휘발유)이 불렸을 때 '아니오 경유요'로 정정."""
    extractor = FakeExtractor(
        [
            LLMExtraction(intent="order", amount=50000),
            LLMExtraction(intent="modify", fuel_type="경유"),
            LLMExtraction(intent="confirm"),
        ]
    )
    agent = FuelingOrderAgent(extractor=extractor)
    state = SessionState.start(car_num="11가1111", saved_fuel_type="휘발유")

    r1 = agent.process_turn(state, "5만원요")
    assert r1.phase == "confirming"
    assert "휘발유" in r1.reply_text

    r2 = agent.process_turn(r1.state, "아니오 경유요")
    assert r2.phase == "confirming"
    assert "경유" in r2.reply_text and "50,000원" in r2.reply_text
    assert r2.should_save_fuel_type is False

    r3 = agent.process_turn(r2.state, "네 맞아요")
    assert r3.phase == "confirmed"
    assert r3.confirmed_order is not None
    assert r3.confirmed_order.fuel_type == "경유"
    assert r3.confirmed_order.amount == 50000


def test_liters_order_converts_amount_with_injected_fuel_prices():
    extractor = FakeExtractor(
        [
            LLMExtraction(intent="order", liters=20.0),
            LLMExtraction(intent="confirm"),
        ]
    )
    agent = FuelingOrderAgent(extractor=extractor)
    state = SessionState.start(car_num="55다5555", saved_fuel_type="경유")

    r1 = agent.process_turn(state, "20리터 넣어주세요", fuel_prices={"휘발유": 1700, "경유": 1500})
    assert r1.phase == "confirming"
    assert r1.draft.liters == 20.0
    assert r1.draft.amount == 30000
    assert "경유" in r1.reply_text and "20리터" in r1.reply_text and "30,000원" in r1.reply_text

    r2 = agent.process_turn(r1.state, "네", fuel_prices={"휘발유": 1700, "경유": 1500})
    assert r2.phase == "confirmed"
    assert r2.confirmed_order is not None
    assert r2.confirmed_order.amount == 30000
    assert r2.confirmed_order.liters == 20.0


def test_deny_without_correction_returns_to_collecting():
    extractor = FakeExtractor(
        [
            LLMExtraction(intent="order", fuel_type="휘발유", amount=50000),
            LLMExtraction(intent="deny"),
            LLMExtraction(intent="order", fuel_type="경유", amount=40000),
        ]
    )
    agent = FuelingOrderAgent(extractor=extractor)
    state = SessionState.start(car_num="77라7777")

    r1 = agent.process_turn(state, "휘발유 5만원")
    assert r1.phase == "confirming"

    r2 = agent.process_turn(r1.state, "아니오 다시 할게요")
    assert r2.phase == "collecting"
    assert r2.draft.fuel_type is None
    assert r2.draft.amount is None

    r3 = agent.process_turn(r2.state, "경유 4만원")
    assert r3.phase == "confirming"
    assert "경유" in r3.reply_text and "40,000원" in r3.reply_text


def test_cancel_and_unsupported_fuel_and_retry_limit():
    extractor = FakeExtractor(
        [
            LLMExtraction(intent="unsupported", unsupported_fuel="고급유"),
            LLMExtraction(intent="unclear"),
            LLMExtraction(intent="unclear"),
            LLMExtraction(intent="unclear"),
            LLMExtraction(intent="cancel"),
        ]
    )
    agent = FuelingOrderAgent(extractor=extractor, max_retries=3)
    state = SessionState.start(car_num="88마8888")

    r1 = agent.process_turn(state, "고급유 5만원")
    assert r1.phase == "collecting"
    assert "고급유" in r1.reply_text and "지원하지 않습니다" in r1.reply_text

    r2 = agent.process_turn(r1.state, "음...")
    r3 = agent.process_turn(r2.state, "어...")
    r4 = agent.process_turn(r3.state, "저기...")
    assert r4.state.retry_count == 3
    assert "화면에서 입력" in r4.reply_text

    r5 = agent.process_turn(r4.state, "그냥 취소할게요")
    assert r5.phase == "canceled"
    assert r5.should_show_qr is False
    assert r5.should_save_fuel_type is False
