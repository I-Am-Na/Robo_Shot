"""프레임마다 나오는 판단을 모아 확정하고, 서버에 보낼지 정한다.

- 같은 번호판의 최근 stable_frames번 판단(window초 이내)이 모두 같은 (라인, is_line)이어야 확정한다.
  → OCR이 한두 번 잘못 읽은 번호는 따로 모여 stable_frames에 못 미치므로 걸러진다.
  → 구역이 바뀌면(진입 → 정지) stable_frames 프레임 뒤에 바로 반영된다.
- 확정된 판단은
  · 처음이면 보낸다
  · 라인/is_line이 바뀌면 보낸다 (진입 구역 → 정지 구역 등)
  · 같은 상태가 계속되면 resend_interval초마다 한 번만 다시 보낸다
  → 매 프레임 PUT /car를 보내지 않는다 (서버 payment 행이 쌓이지 않게).
- forget_after초 동안 안 보인 차량은 잊는다 (다음에 오면 다시 '처음').
"""

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    plate: str
    line_num: int
    is_line: bool
    t: float  # 초 (time.monotonic 등)


@dataclass(frozen=True)
class Report:
    """서버에 보낼 PUT /car 내용."""

    car_num: str
    line_num: int
    is_line: bool
    reason: str  # new | changed | resend


class Stabilizer:
    def __init__(
        self,
        stable_frames: int = 5,
        window: float = 2.0,
        resend_interval: float = 30.0,
        forget_after: float = 10.0,
    ):
        self.stable_frames = stable_frames
        self.window = window
        self.resend_interval = resend_interval
        self.forget_after = forget_after
        self._history: dict[str, deque[Observation]] = {}
        self._last_seen: dict[str, float] = {}
        self._sent: dict[str, tuple[tuple[int, bool], float]] = {}  # plate -> ((line, is_line), t)

    def update(self, observations: list[Observation], now: float) -> list[Report]:
        for ob in observations:
            self._history.setdefault(ob.plate, deque()).append(ob)
            self._last_seen[ob.plate] = ob.t

        reports: list[Report] = []
        for plate, hist in list(self._history.items()):
            while hist and now - hist[0].t > self.window:
                hist.popleft()
            if len(hist) < self.stable_frames:
                continue
            recent = list(hist)[-self.stable_frames:]
            states = {(o.line_num, o.is_line) for o in recent}
            if len(states) != 1:
                continue  # 구역 경계에서 왔다 갔다 하는 중
            state = states.pop()

            last = self._sent.get(plate)
            if last is None:
                reason = "new"
            elif last[0] != state:
                reason = "changed"
            elif now - last[1] >= self.resend_interval:
                reason = "resend"
            else:
                continue
            self._sent[plate] = (state, now)
            reports.append(Report(car_num=plate, line_num=state[0], is_line=state[1], reason=reason))

        self._forget(now)
        return reports

    def _forget(self, now: float) -> None:
        for plate, seen in list(self._last_seen.items()):
            if now - seen > self.forget_after:
                self._last_seen.pop(plate, None)
                self._history.pop(plate, None)
                self._sent.pop(plate, None)
