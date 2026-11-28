"""터미널 대화 시뮬레이터.

프론트엔드/백엔드 연동 전, GPT-4o 프롬프트와 대화 흐름을 단독으로 테스트할 때 사용한다.

실행 예:
  # 신규 방문 차량 테스트
  python3 -m robo_shot_agent --car-num 12가3456

  # 재방문 차량 테스트 (기존 유종: 휘발유)
  python3 -m robo_shot_agent --car-num 12가3456 --saved-fuel 휘발유
"""

from __future__ import annotations

import argparse
import sys

from robo_shot_agent.agent import FuelingOrderAgent
from robo_shot_agent.llm import OpenAIOrderExtractor
from robo_shot_agent.schemas import DEFAULT_FUEL_PRICES, FuelType, SessionState


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Robo-Shot AI Agent CLI 시뮬레이터")
    parser.add_argument("--car-num", default="12가3456", help="테스트 차량번호")
    parser.add_argument(
        "--saved-fuel",
        choices=["휘발유", "경유"],
        default=None,
        help="재방문 차량 시뮬레이션용 저장 유종 (생략하면 신규 방문)",
    )
    parser.add_argument("--model", default="gpt-4o", help="OpenAI 모델명 (기본: gpt-4o)")
    parser.add_argument("--gasoline-price", type=int, default=DEFAULT_FUEL_PRICES["휘발유"], help="휘발유 리터당 단가")
    parser.add_argument("--diesel-price", type=int, default=DEFAULT_FUEL_PRICES["경유"], help="경유 리터당 단가")
    parser.add_argument("--env", default=".env", help=".env 파일 경로")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fuel_prices: dict[FuelType, int] = {
        "휘발유": args.gasoline_price,
        "경유": args.diesel_price,
    }

    try:
        extractor = OpenAIOrderExtractor(model=args.model, dotenv_path=args.env)
    except ValueError as exc:
        print(f"[오류] {exc}", file=sys.stderr)
        return 1

    agent = FuelingOrderAgent(extractor=extractor, default_fuel_prices=fuel_prices)
    state = SessionState.start(car_num=args.car_num, saved_fuel_type=args.saved_fuel)

    visit_label = f"재방문 ({args.saved_fuel})" if state.is_revisit else "신규 방문"
    print(f"=== Robo-Shot AI Agent 테스트 ({args.car_num} / {visit_label}) ===")
    print("종료하려면 quit 또는 Ctrl+C 를 입력하세요.\n")
    print(f"[로보샷 TTS] {agent.initial_greeting(state)}")

    while state.phase not in ("confirmed", "canceled"):
        try:
            user_text = input("\n[운전자 STT] > ")
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            return 0
        if user_text.strip().lower() in ("quit", "exit"):
            print("종료합니다.")
            return 0

        result = agent.process_turn(state, user_text, fuel_prices=fuel_prices)
        state = result.state

        print(f"[로보샷 TTS] {result.reply_text}")
        print(
            f"  (intent={result.intent}, phase={result.phase}, "
            f"draft={result.draft.model_dump()}, "
            f"save_fuel={result.should_save_fuel_type}, show_qr={result.should_show_qr})"
        )
        if result.confirmed_order:
            print(f"  => 확정 주문: {result.confirmed_order.model_dump()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
