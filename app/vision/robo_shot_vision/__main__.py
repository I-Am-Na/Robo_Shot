"""실행: python -m robo_shot_vision --config config.json [--source 0] [--show] [--dry-run]

--show     화면에 라인 구역·검출 박스·판단 결과를 그려서 보여준다 (q로 종료)
--dry-run  서버에 보내지 않고 보낼 내용만 출력한다
"""

import argparse
import logging
import time

from robo_shot_vision.config import Config, load_config
from robo_shot_vision.pipeline import FrameResult, Pipeline
from robo_shot_vision.server_client import ServerClient
from robo_shot_vision.stabilizer import Stabilizer

logger = logging.getLogger("robo_shot_vision")


_INSTALL_HINT = "필요한 라이브러리가 없습니다: {e}\n  → cd app/vision && pip install -r requirements.txt"


def build_detector(cfg: Config):
    from pathlib import Path

    if not Path(cfg.model_path).exists():
        raise SystemExit(f"모델 파일이 없습니다: {cfg.model_path}\n  → 학습된 best.pt를 models/ 에 두거나 config의 model_path를 바꿔주세요.")
    try:
        from robo_shot_vision.yolo_detector import YoloPlateDetector

        return YoloPlateDetector(
            cfg.model_path, cfg.plate_classes, cfg.vehicle_classes, conf=cfg.yolo_conf, device=cfg.device
        )
    except ImportError as e:
        raise SystemExit(_INSTALL_HINT.format(e=e)) from e


def build_reader(cfg: Config):
    try:
        from robo_shot_vision.ocr_reader import EasyOcrPlateReader

        return EasyOcrPlateReader(gpu=cfg.ocr_gpu)
    except ImportError as e:
        raise SystemExit(_INSTALL_HINT.format(e=e)) from e


def build_pipeline(cfg: Config, dry_run: bool) -> Pipeline:
    return Pipeline(
        detector=build_detector(cfg),
        reader=build_reader(cfg),
        zones=cfg.zones(),
        stabilizer=Stabilizer(cfg.stable_frames, cfg.window, cfg.resend_interval, cfg.forget_after),
        sender=None if dry_run else ServerClient(cfg.server_url),
        min_det_conf=cfg.min_det_conf,
        min_ocr_conf=cfg.min_ocr_conf,
    )


def draw(frame, cfg: Config, result: FrameResult):
    import cv2
    import numpy as np

    for z in cfg.lines:
        cv2.polylines(frame, [np.array(z.stop, np.int32)], True, (0, 200, 0), 2)
        cv2.putText(frame, f"LINE {z.line_num} STOP", tuple(map(int, z.stop[0])), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 200, 0), 2)
        if z.approach:
            cv2.polylines(frame, [np.array(z.approach, np.int32)], True, (0, 200, 255), 1)
    for r in result.readings:
        x1, y1, x2, y2 = map(int, r.detection.plate_bbox)
        ok = r.skipped is None
        color = (0, 255, 0) if ok and r.is_line else (0, 200, 255) if ok else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        # cv2.putText은 한글을 못 그려서 영문/숫자로 표시
        label = (f"L{r.line_num} {'IN' if r.is_line else 'APPROACH'} {r.detection.confidence:.2f}"
                 if ok else f"{r.skipped} {r.detection.confidence:.2f}")
        cv2.putText(frame, label, (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        if r.detection.vehicle_bbox:
            vx1, vy1, vx2, vy2 = map(int, r.detection.vehicle_bbox)
            cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), (255, 150, 0), 1)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description="Robo_Shot 차량 진입 감지 → PUT /car")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--source", help="설정의 source 대신 사용 (웹캠 번호/영상 파일/rtsp)")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    cfg = load_config(args.config)
    if args.source is not None:
        cfg.source = int(args.source) if args.source.isdigit() else args.source

    import cv2

    pipeline = build_pipeline(cfg, args.dry_run)
    cap = cv2.VideoCapture(cfg.source)
    if not cap.isOpened():
        raise SystemExit(f"영상을 열 수 없습니다: {cfg.source}")
    logger.info("시작: source=%s server=%s dry_run=%s", cfg.source, cfg.server_url, args.dry_run)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                logger.info("영상 끝 또는 프레임 없음")
                break
            result = pipeline.process(frame, time.monotonic())
            for report, response, error in result.sent:
                if error:
                    logger.warning("전송 실패 %s: %s", report, error)
                elif response is None:
                    logger.info("[dry-run] PUT /car %s %s번 라인 is_line=%s (%s)",
                                report.car_num, report.line_num, report.is_line, report.reason)
                else:
                    logger.info("PUT /car %s %s번 라인 is_line=%s (%s) → %s, status=%s",
                                report.car_num, report.line_num, report.is_line, report.reason,
                                response.get("message"), response.get("status"))
            if args.show:
                cv2.imshow("robo_shot_vision", draw(frame, cfg, result))
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
