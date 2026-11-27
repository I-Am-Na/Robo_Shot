"""모델 갈아끼우는 자리. 학습된 모델은 이 두 인터페이스만 맞추면 된다."""

from dataclasses import dataclass
from typing import Any, Protocol

from robo_shot_vision.geometry import BBox


@dataclass
class PlateDetection:
    """프레임에서 찾은 번호판 1개."""

    plate_bbox: BBox
    confidence: float
    crop: Any  # 번호판 부분 이미지 (numpy 배열)
    vehicle_bbox: BBox | None = None  # 번호판이 속한 차량 박스 (있으면 라인 판단에 사용)


class PlateDetector(Protocol):
    def detect(self, frame: Any) -> list[PlateDetection]: ...


class PlateReader(Protocol):
    def read(self, crop: Any) -> tuple[str, float]:
        """번호판 이미지 → (문자열, 신뢰도 0~1)"""
        ...
