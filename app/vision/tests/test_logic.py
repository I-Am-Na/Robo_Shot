import json

import pytest

from robo_shot_vision.config import load_config
from robo_shot_vision.geometry import LineZone, LineZones, point_in_polygon
from robo_shot_vision.interfaces import PlateDetection
from robo_shot_vision.pipeline import Pipeline
from robo_shot_vision.plate import normalize_plate
from robo_shot_vision.stabilizer import Observation, Report, Stabilizer

SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]
ZONES = LineZones([
    LineZone(1, stop=[(0, 50), (50, 50), (50, 100), (0, 100)], approach=[(0, 0), (50, 0), (50, 50), (0, 50)]),
    LineZone(2, stop=[(60, 50), (110, 50), (110, 100), (60, 100)]),
])


# --- geometry ---

def test_point_in_polygon():
    assert point_in_polygon((5, 5), SQUARE)
    assert not point_in_polygon((15, 5), SQUARE)


@pytest.mark.parametrize("bbox, expected", [
    ((10, 60, 40, 90), (1, True)),     # 아래 가운데 (25, 90) → 1번 정지 구역
    ((10, 10, 40, 40), (1, False)),    # (25, 40) → 1번 진입 구역
    ((70, 60, 100, 95), (2, True)),    # 2번 정지 구역
    ((70, 10, 100, 40), (None, False)),  # 2번은 진입 구역 없음
    ((200, 200, 220, 220), (None, False)),
])
def test_line_zones_locate(bbox, expected):
    assert ZONES.locate(bbox) == expected


# --- plate ---

@pytest.mark.parametrize("raw, expected", [
    ("12가3456", "12가3456"),
    ("12가 3456", "12가3456"),
    ("12-가-3456", "12가3456"),
    ("123가4567", "123가4567"),
    ("서울12가3456", "서울12가3456"),
    ("I2가34S6", "12가3456"),   # OCR이 1→I, 5→S로 읽은 경우
    ("O1나2B34", "01나2834"),
])
def test_normalize_plate(raw, expected):
    assert normalize_plate(raw) == expected


@pytest.mark.parametrize("raw", ["", "12가345", "가3456", "1234567", "12AB3456", "hello"])
def test_normalize_plate_rejects(raw):
    assert normalize_plate(raw) is None


# --- stabilizer ---

def obs(plate="12가3456", line=1, is_line=True, t=0.0):
    return Observation(plate, line, is_line, t)


def feed(stab, n, t0=0.0, dt=0.1, **kw):
    out = []
    for i in range(n):
        t = t0 + i * dt
        out += stab.update([obs(t=t, **kw)], t)
    return out


def test_reports_once_after_stable_frames():
    stab = Stabilizer(stable_frames=5, window=2.0, resend_interval=30.0)
    reports = feed(stab, 4)
    assert reports == []
    reports = feed(stab, 20, t0=0.4)
    assert reports == [Report("12가3456", 1, True, "new")]


def test_noisy_ocr_misread_is_ignored():
    stab = Stabilizer(stable_frames=5)
    assert stab.update([obs(plate="12가3458")], 0.0) == []  # 한 번 잘못 읽음
    reports = feed(stab, 10, t0=0.1)
    assert [r.car_num for r in reports] == ["12가3456"]


def test_reports_again_when_state_changes():
    stab = Stabilizer(stable_frames=3, window=1.0)
    r1 = feed(stab, 5, is_line=False)  # 진입 구역
    r2 = feed(stab, 15, t0=1.0, is_line=True)  # 정지 구역으로 들어옴
    assert [(r.is_line, r.reason) for r in r1 + r2] == [(False, "new"), (True, "changed")]


def test_state_change_is_reported_within_stable_frames():
    stab = Stabilizer(stable_frames=5, window=2.0)
    feed(stab, 20, is_line=False)  # 2초 동안 진입 구역
    reports = feed(stab, 5, t0=2.0, is_line=True)  # 정지 구역 5프레임
    assert [(r.is_line, r.reason) for r in reports] == [(True, "changed")]


def test_flickering_on_zone_border_is_not_reported():
    stab = Stabilizer(stable_frames=3, window=2.0)
    out = []
    for i in range(10):
        out += stab.update([obs(t=i * 0.1, is_line=i % 2 == 0)], i * 0.1)
    assert out == []


def test_resend_interval():
    stab = Stabilizer(stable_frames=3, window=1.0, resend_interval=5.0, forget_after=100)
    reports = feed(stab, 70, dt=0.1)  # 0~6.9초
    assert [r.reason for r in reports] == ["new", "resend"]


def test_forgets_car_that_left():
    stab = Stabilizer(stable_frames=3, window=1.0, forget_after=3.0)
    assert len(feed(stab, 5)) == 1
    stab.update([], 10.0)  # 오래 안 보임
    assert [r.reason for r in feed(stab, 5, t0=20.0)] == ["new"]


# --- pipeline ---

class FakeDetector:
    def __init__(self, detections):
        self.detections = detections

    def detect(self, frame):
        return self.detections


class FakeReader:
    def __init__(self, text, conf=0.9):
        self.text, self.conf = text, conf

    def read(self, crop):
        return self.text, self.conf


class FakeSender:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def visit(self, report):
        if self.fail:
            raise RuntimeError("server down")
        self.calls.append(report)
        return {"success": True, "message": "created", "status": "ready"}


def det(bbox=(10, 60, 40, 90), conf=0.9, vehicle=None):
    return PlateDetection(plate_bbox=bbox, confidence=conf, crop="crop", vehicle_bbox=vehicle)


def make(dets, text="12가 3456", ocr_conf=0.9, sender=None):
    return Pipeline(FakeDetector(dets), FakeReader(text, ocr_conf), ZONES, Stabilizer(stable_frames=3),
                    sender, min_det_conf=0.5, min_ocr_conf=0.4)


def run(p, frames):
    out = []
    for i in range(frames):
        out.append(p.process(None, i * 0.1))
    return out


def test_pipeline_sends_put_car_once_stable():
    sender = FakeSender()
    run(make([det()], sender=sender), 10)
    assert sender.calls == [Report("12가3456", 1, True, "new")]


def test_pipeline_uses_vehicle_bbox_for_line():
    sender = FakeSender()
    # 번호판 박스는 구역 밖이지만 차량 박스 아래쪽은 2번 정지 구역
    run(make([det(bbox=(200, 0, 210, 5), vehicle=(70, 60, 100, 95))], sender=sender), 5)
    assert [(r.line_num, r.is_line) for r in sender.calls] == [(2, True)]


@pytest.mark.parametrize("kwargs, reason", [
    ({"dets": [det(conf=0.3)]}, "low_det_conf"),
    ({"dets": [det()], "ocr_conf": 0.1}, "low_ocr_conf"),
    ({"dets": [det()], "text": "abc"}, "bad_format"),
    ({"dets": [det(bbox=(200, 200, 220, 220))]}, "outside_zone"),
])
def test_pipeline_skips(kwargs, reason):
    sender = FakeSender()
    results = run(make(sender=sender, **kwargs), 5)
    assert results[-1].readings[0].skipped == reason
    assert sender.calls == []


def test_pipeline_dry_run_and_server_failure_keep_running():
    dry = run(make([det()], sender=None), 5)
    assert any(s for r in dry for s in r.sent)
    failing = run(make([det()], sender=FakeSender(fail=True)), 5)
    errors = [e for r in failing for (_, _, e) in r.sent if e]
    assert errors == ["server down"]


# --- config ---

def test_load_example_config():
    cfg = load_config("config.example.json")
    assert cfg.source == 0
    assert [z.line_num for z in cfg.lines] == [1, 2]
    assert cfg.zones().locate((200, 500, 300, 650)) == (1, True)


def test_config_rejects_bad_line(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"lines": [{"line_num": 3, "stop": [[0, 0], [1, 0], [1, 1]]}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="line_num"):
        load_config(p)
    p.write_text(json.dumps({"typo_key": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="알 수 없는 설정"):
        load_config(p)
