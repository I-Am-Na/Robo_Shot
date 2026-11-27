"""학습된 YOLO(ultralytics) 모델로 번호판(+차량)을 찾는다.

모델 클래스 이름은 config의 plate_classes / vehicle_classes 로 맞춘다.
- 번호판만 학습한 모델: plate_classes만 맞으면 된다 (라인 판단은 번호판 박스로)
- 차량+번호판 모델: 번호판 중심이 들어 있는 차량 박스를 짝지어 라인 판단은 차량 박스로
"""

from typing import Any

from robo_shot_vision.geometry import BBox
from robo_shot_vision.interfaces import PlateDetection


def _contains(outer: BBox, inner: BBox) -> bool:
    cx, cy = (inner[0] + inner[2]) / 2, (inner[1] + inner[3]) / 2
    return outer[0] <= cx <= outer[2] and outer[1] <= cy <= outer[3]


class YoloPlateDetector:
    def __init__(
        self,
        model_path: str,
        plate_classes: list[str],
        vehicle_classes: list[str],
        conf: float = 0.25,
        device: str | None = None,
        crop_padding: float = 0.08,
    ):
        from ultralytics import YOLO  # 무거운 라이브러리라 실제 사용 시에만 불러온다

        self.model = YOLO(model_path)
        self.names: dict[int, str] = self.model.names
        self.plate_classes = {c.lower() for c in plate_classes}
        self.vehicle_classes = {c.lower() for c in vehicle_classes}
        self.conf = conf
        self.device = device
        self.crop_padding = crop_padding

        known = {n.lower() for n in self.names.values()}
        if not (self.plate_classes & known):
            raise ValueError(
                f"모델 클래스 {sorted(known)} 중에 번호판 클래스 {sorted(self.plate_classes)}가 없습니다. "
                "config의 plate_classes를 모델 클래스 이름에 맞춰주세요."
            )

    def detect(self, frame: Any) -> list[PlateDetection]:
        result = self.model.predict(frame, conf=self.conf, device=self.device, verbose=False)[0]
        plates: list[tuple[BBox, float]] = []
        vehicles: list[BBox] = []
        for xyxy, cls, conf in zip(result.boxes.xyxy.tolist(), result.boxes.cls.tolist(), result.boxes.conf.tolist()):
            name = self.names[int(cls)].lower()
            box: BBox = tuple(xyxy)  # type: ignore[assignment]
            if name in self.plate_classes:
                plates.append((box, float(conf)))
            elif name in self.vehicle_classes:
                vehicles.append(box)

        h, w = frame.shape[:2]
        detections = []
        for box, conf in plates:
            vehicle = next((v for v in vehicles if _contains(v, box)), None)
            detections.append(PlateDetection(
                plate_bbox=box, confidence=conf, crop=self._crop(frame, box, w, h), vehicle_bbox=vehicle,
            ))
        return detections

    def _crop(self, frame: Any, box: BBox, w: int, h: int) -> Any:
        x1, y1, x2, y2 = box
        px, py = (x2 - x1) * self.crop_padding, (y2 - y1) * self.crop_padding
        x1, y1 = max(0, int(x1 - px)), max(0, int(y1 - py))
        x2, y2 = min(w, int(x2 + px)), min(h, int(y2 + py))
        return frame[y1:y2, x1:x2]
