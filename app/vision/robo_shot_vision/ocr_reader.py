"""번호판 이미지 → 문자열 (EasyOCR).

다른 OCR(PaddleOCR, 직접 학습한 모델 등)로 바꾸려면 read(crop) -> (text, conf) 만 맞춘 클래스를 만들고
__main__.py 의 build_reader 에서 바꿔 끼우면 된다.
"""

from typing import Any

from robo_shot_vision.plate import PLATE_ALLOWLIST


class EasyOcrPlateReader:
    def __init__(self, gpu: bool = False, upscale_height: int = 64):
        import easyocr  # 무거운 라이브러리라 실제 사용 시에만 불러온다

        self.reader = easyocr.Reader(["ko"], gpu=gpu)
        self.upscale_height = upscale_height

    def read(self, crop: Any) -> tuple[str, float]:
        if crop is None or getattr(crop, "size", 0) == 0:
            return "", 0.0
        crop = self._prepare(crop)
        results = self.reader.readtext(crop, allowlist=PLATE_ALLOWLIST, detail=1, paragraph=False)
        if not results:
            return "", 0.0
        # 2줄 번호판(위: 지역+숫자, 아래: 한글+숫자)도 위→아래, 왼→오 순으로 이어 붙인다
        results.sort(key=lambda r: (round(min(p[1] for p in r[0]) / 10), min(p[0] for p in r[0])))
        text = "".join(r[1] for r in results)
        conf = sum(r[2] for r in results) / len(results)
        return text, float(conf)

    def _prepare(self, crop: Any) -> Any:
        import cv2

        h = crop.shape[0]
        if 0 < h < self.upscale_height:
            scale = self.upscale_height / h
            crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        return cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
