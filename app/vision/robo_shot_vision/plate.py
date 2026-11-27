"""OCR 결과를 한국 번호판 형식으로 다듬기."""

import re

# 12가3456 / 123가4567 / 서울12가3456
PLATE_RE = re.compile(r"^(?:[가-힣]{2})?\d{2,3}[가-힣]\d{4}$")

# OCR이 숫자를 영문으로 잘못 읽는 경우
_DIGIT_FIX = str.maketrans({
    "O": "0", "o": "0", "D": "0", "Q": "0",
    "I": "1", "l": "1", "|": "1", "i": "1",
    "Z": "2", "z": "2",
    "S": "5", "s": "5",
    "G": "6", "b": "6",
    "B": "8",
    "T": "7",
})

_STRIP = re.compile(r"[\s\-_.·,:'\"`]")


def normalize_plate(text: str) -> str | None:
    """OCR 문자열 → '12가3456'. 번호판 형식이 아니면 None."""
    if not text:
        return None
    s = _STRIP.sub("", text)
    # 한글이 아닌 글자에만 숫자 보정 적용
    s = "".join(ch if "가" <= ch <= "힣" else ch.translate(_DIGIT_FIX) for ch in s)
    return s if PLATE_RE.match(s) else None


# EasyOCR allowlist 용: 번호판에 쓰이는 한글 + 지역명 + 숫자
PLATE_HANGUL = (
    "가나다라마거너더러머버서어저고노도로모보소오조구누두루무부수우주아바사자배하허호"
    "서울부산대구인천광주대전울산세종경기강원충북충남전북전남경북경남제주"
)
PLATE_ALLOWLIST = "0123456789" + "".join(sorted(set(PLATE_HANGUL)))
