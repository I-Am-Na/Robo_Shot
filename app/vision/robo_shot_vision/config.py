"""설정 파일(JSON) 읽기. 예시는 config.example.json."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from robo_shot_vision.geometry import LineZone, LineZones


@dataclass
class Config:
    server_url: str = "http://localhost:8000"
    source: str | int = 0  # 웹캠 번호, 영상 파일 경로, rtsp:// 주소

    # 모델
    model_path: str = "models/best.pt"
    plate_classes: list[str] = field(default_factory=lambda: ["plate", "license_plate", "license-plate"])
    vehicle_classes: list[str] = field(default_factory=lambda: ["car", "vehicle", "truck", "bus"])
    device: str | None = None  # None=자동, "cpu", "0"(GPU)
    ocr_gpu: bool = False

    # 판단 기준
    yolo_conf: float = 0.25  # YOLO가 박스를 내놓는 최소 신뢰도
    min_det_conf: float = 0.5  # 번호판으로 인정할 최소 신뢰도 (README 미정 사항: 번호판 인식 신뢰도 기준값)
    min_ocr_conf: float = 0.4
    stable_frames: int = 5  # window초 안에 같은 판단이 몇 번 나와야 확정할지
    window: float = 2.0
    resend_interval: float = 30.0
    forget_after: float = 10.0

    # 라인 구역 (픽셀 좌표 다각형). calibrate 도구로 찍어서 넣는다.
    lines: list[LineZone] = field(default_factory=list)

    def zones(self) -> LineZones:
        return LineZones(self.lines)


def _zone(d: dict) -> LineZone:
    if d.get("line_num") not in (1, 2):
        raise ValueError(f"line_num은 1 또는 2여야 합니다: {d}")
    stop = [tuple(p) for p in d["stop"]]
    approach = [tuple(p) for p in d["approach"]] if d.get("approach") else None
    for name, poly in (("stop", stop), ("approach", approach)):
        if poly is not None and len(poly) < 3:
            raise ValueError(f"{d['line_num']}번 라인 {name} 구역은 점이 3개 이상이어야 합니다.")
    return LineZone(line_num=d["line_num"], stop=stop, approach=approach)


def load_config(path: str | Path) -> Config:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    lines = [_zone(z) for z in raw.pop("lines", [])]
    raw.pop("_comment", None)
    unknown = set(raw) - set(Config.__dataclass_fields__)
    if unknown:
        raise ValueError(f"알 수 없는 설정: {sorted(unknown)}")
    cfg = Config(**raw, lines=lines)
    if isinstance(cfg.source, str) and cfg.source.isdigit():
        cfg.source = int(cfg.source)
    return cfg
