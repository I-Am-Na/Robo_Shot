"""화면 좌표 계산: 차량이 어느 라인의 어느 구역에 있는지."""

from dataclasses import dataclass

Point = tuple[float, float]
BBox = tuple[float, float, float, float]  # x1, y1, x2, y2 (픽셀)


def point_in_polygon(p: Point, polygon: list[Point]) -> bool:
    """ray casting. 꼭짓점 3개 이상."""
    x, y = p
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_cross = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_cross:
                inside = not inside
    return inside


def anchor_point(bbox: BBox) -> Point:
    """차량 위치 기준점: 박스 아래쪽 가운데 (바퀴가 닿는 곳)."""
    x1, _, x2, y2 = bbox
    return ((x1 + x2) / 2, y2)


@dataclass(frozen=True)
class LineZone:
    """주유 라인 1개의 화면 구역.

    stop:     정지 구역. 이 안에 들어오면 라인에 정상 진입(is_line=true)
    approach: 진입 구역(선택). 라인 쪽으로 들어오는 중이지만 아직 정지 구역 밖(is_line=false)
    """

    line_num: int
    stop: list[Point]
    approach: list[Point] | None = None


class LineZones:
    def __init__(self, zones: list[LineZone]):
        if not zones:
            raise ValueError("라인 구역이 최소 1개 필요합니다.")
        self.zones = zones

    def locate(self, bbox: BBox) -> tuple[int | None, bool]:
        """(line_num, is_line). 어느 구역에도 없으면 (None, False). 정지 구역이 진입 구역보다 우선."""
        p = anchor_point(bbox)
        for z in self.zones:
            if point_in_polygon(p, z.stop):
                return z.line_num, True
        for z in self.zones:
            if z.approach and point_in_polygon(p, z.approach):
                return z.line_num, False
        return None, False
