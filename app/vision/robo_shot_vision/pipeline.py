"""프레임 1장 처리: 검출 → OCR → 형식 보정 → 라인 판단 → 확정 → 서버 전송.

모델·카메라·HTTP와 분리되어 있어서 가짜 detector/reader/client로 테스트한다.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from robo_shot_vision.geometry import LineZones
from robo_shot_vision.interfaces import PlateDetection, PlateDetector, PlateReader
from robo_shot_vision.plate import normalize_plate
from robo_shot_vision.stabilizer import Observation, Report, Stabilizer

logger = logging.getLogger(__name__)


class VisitSender(Protocol):
    def visit(self, report: Report) -> dict: ...


@dataclass
class Reading:
    """화면 표시용: 검출 1개를 어떻게 판단했는지."""

    detection: PlateDetection
    raw_text: str | None = None
    plate: str | None = None
    ocr_conf: float = 0.0
    line_num: int | None = None
    is_line: bool = False
    skipped: str | None = None  # 버린 이유


@dataclass
class FrameResult:
    readings: list[Reading] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)
    sent: list[tuple[Report, dict | None, str | None]] = field(default_factory=list)  # (report, 응답, 에러)


class Pipeline:
    def __init__(
        self,
        detector: PlateDetector,
        reader: PlateReader,
        zones: LineZones,
        stabilizer: Stabilizer,
        sender: VisitSender | None,
        min_det_conf: float = 0.5,
        min_ocr_conf: float = 0.4,
    ):
        self.detector = detector
        self.reader = reader
        self.zones = zones
        self.stabilizer = stabilizer
        self.sender = sender  # None이면 dry-run (서버에 보내지 않음)
        self.min_det_conf = min_det_conf
        self.min_ocr_conf = min_ocr_conf

    def process(self, frame: Any, now: float) -> FrameResult:
        result = FrameResult()
        observations: list[Observation] = []

        for det in self.detector.detect(frame):
            r = Reading(detection=det)
            result.readings.append(r)
            if det.confidence < self.min_det_conf:
                r.skipped = "low_det_conf"
                continue

            r.raw_text, r.ocr_conf = self.reader.read(det.crop)
            if r.ocr_conf < self.min_ocr_conf:
                r.skipped = "low_ocr_conf"
                continue
            r.plate = normalize_plate(r.raw_text)
            if r.plate is None:
                r.skipped = "bad_format"
                continue

            r.line_num, r.is_line = self.zones.locate(det.vehicle_bbox or det.plate_bbox)
            if r.line_num is None:
                r.skipped = "outside_zone"
                continue
            observations.append(Observation(r.plate, r.line_num, r.is_line, now))

        result.reports = self.stabilizer.update(observations, now)
        for report in result.reports:
            if self.sender is None:
                result.sent.append((report, None, None))
                continue
            try:
                result.sent.append((report, self.sender.visit(report), None))
            except Exception as e:  # 서버 오류가 나도 영상 처리는 계속한다
                logger.warning("PUT /car 실패: %s", e)
                result.sent.append((report, None, str(e)))
        return result
