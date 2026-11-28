# Robo_Shot AI Agent

PRD v1.3 기준 **음성 주문 의도 분석 · 복창 · `"네 / 아니오"` 확인 대화**를 담당하는 독립 Python 패키지입니다.  
FastAPI, DB, 프론트엔드에 직접 의존하지 않도록 분리되어 있어, 팀 합의 후 **`app/backend` 내부 통합** 또는 **별도 `app/agent` 서버 실행** 어느 쪽으로도 그대로 이식할 수 있습니다.

## 주요 기능 (PRD v1.3 반영)

- **신규 방문 vs 재방문 분기**: `saved_fuel_type`이 있으면 유종 질문을 생략하고 금액/용량만 받음
- **금액 + 용량(리터) 지원**: `"5만원"`, `"삼만 오천원"`, `"20리터"` 등 자연어 추출 및 유가(`fuel_prices`) 기반 금액 환산
- **혼유·번호판 오인식 방지 복창**: 재방문 차량도 반드시 유종을 포함해 복창 (`"휘발유 50,000원 주유하겠습니다. 맞으신가요?"`)
- **안전한 확정 시점**: 고객이 `"네"`로 승인한 시점에만 `should_save_fuel_type=True`, `should_show_qr=True`, `confirmed_order`를 반환
- **정정 / 거절 / 취소 / 미지원 유종 처리**: `"아니오 경유요"`, `"3만원으로 바꿔줘"`, `"고급유"`, `"취소"` 등 멀티턴 대화 처리

## 구조

| 파일 | 역할 |
|---|---|
| `robo_shot_agent/schemas.py` | 백엔드(`FuelType`, `amount`)·프론트(`OrderPhase`)와 호환되는 입출력 Pydantic 모델 |
| `robo_shot_agent/prompts.py` | GPT-4o System/User 프롬프트 템플릿 (프롬프트 튜닝 전용) |
| `robo_shot_agent/llm.py` | LangChain `ChatOpenAI(model="gpt-4o")` + `with_structured_output` 어댑터 |
| `robo_shot_agent/agent.py` | 상태 전이 및 안전 규칙을 강제하는 `FuelingOrderAgent` |
| `robo_shot_agent/__main__.py` | 터미널 대화 테스트용 CLI |
| `tests/test_agent.py` | OpenAI 호출 없이 모든 시나리오를 검증하는 단위 테스트 |

## 단독 테스트 실행

1. 단위 테스트 (API 키 없이 실행)
   ```bash
   cd app/agent
   env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
   ```

2. GPT-4o 실제 대화 CLI 테스트
   ```bash
   cd app/agent
   cp .env.example .env   # OPENAI_API_KEY 입력
   python3 -m robo_shot_agent --car-num 12가3456
   python3 -m robo_shot_agent --car-num 12가3456 --saved-fuel 휘발유
   ```

## 추후 이식 가이드

### Case A. `app/backend` 내부로 통합할 때
1. `robo_shot_agent/`의 `schemas.py`, `prompts.py`, `llm.py`, `agent.py`를 `app/backend/src/`로 이동
2. FastAPI 라우터(예: `POST /agent/turn`)에서 `agent.process_turn(state, user_text, fuel_prices=...)` 호출
3. `result.should_save_fuel_type`가 `True`일 때 기존 `OrderFuelTypeUseCase.execute(car_num, fuel_type)` 호출
4. 프론트엔드(`useOrderStore.ts`)에서 `result.reply_text`를 TTS 출력하고, `result.should_show_qr`가 `True`일 때 결제 QR 표시

### Case B. `app/agent`를 별도 서비스로 띄울 때
- `app/agent/` 아래에 `server.py`(FastAPI 래퍼)만 추가하고 `agent.process_turn(...)`을 엔드포인트로 노출
