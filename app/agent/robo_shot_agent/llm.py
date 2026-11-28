"""OpenAI GPT-4o (LangChain) 어댑터.

테스트에서는 LLMExtractor Protocol을 구현한 가짜 객체를 주입해
API 키나 네트워크 없이도 모든 시나리오를 검증할 수 있다.
"""

from __future__ import annotations

import os
from typing import Any, Protocol

from dotenv import load_dotenv

from robo_shot_agent.prompts import build_order_prompt
from robo_shot_agent.schemas import LLMExtraction


class LLMExtractor(Protocol):
    """프롬프트 입력 dict를 받아 정형화된 LLMExtraction을 반환하는 인터페이스."""

    def extract(self, prompt_inputs: dict[str, Any]) -> LLMExtraction: ...


class OpenAIOrderExtractor:
    """LangChain ChatOpenAI(gpt-4o) + with_structured_output 기반 추출기."""

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        api_key: str | None = None,
        dotenv_path: str | None = ".env",
        timeout: float = 15.0,
    ) -> None:
        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path)
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "OPENAI_API_KEY가 설정되지 않았습니다. .env 파일 또는 api_key 인자를 확인해주세요."
            )

        from langchain_openai import ChatOpenAI

        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=resolved_key,
            timeout=timeout,
        )
        self._prompt = build_order_prompt()
        self._chain = self._prompt | self._llm.with_structured_output(LLMExtraction)

    def extract(self, prompt_inputs: dict[str, Any]) -> LLMExtraction:
        result = self._chain.invoke(prompt_inputs)
        if isinstance(result, LLMExtraction):
            return result
        return LLMExtraction.model_validate(result)
