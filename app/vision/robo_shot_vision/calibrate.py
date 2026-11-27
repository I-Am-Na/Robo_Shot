"""라인 구역 찍기 도구.

python -m robo_shot_vision.calibrate --source 0          (웹캠 첫 프레임)
python -m robo_shot_vision.calibrate --source sample.jpg (사진/영상 파일)

조작
  마우스 왼쪽 클릭 : 점 추가
  1 / 2            : 1번 / 2번 라인 선택
  s / a            : 정지 구역(stop) / 진입 구역(approach) 선택
  z                : 지금 구역의 마지막 점 지우기
  p                : config.json에 붙여 넣을 "lines" JSON 출력
  q                : 종료 (종료할 때도 출력)
"""

import argparse
import json


def main() -> None:
    import cv2
    import numpy as np

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0")
    args = parser.parse_args()
    src = int(args.source) if args.source.isdigit() else args.source

    if isinstance(src, str) and src.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
        base = cv2.imread(src)
    else:
        cap = cv2.VideoCapture(src)
        ok, base = cap.read()
        cap.release()
        if not ok:
            raise SystemExit(f"영상을 열 수 없습니다: {src}")
    if base is None:
        raise SystemExit(f"이미지를 열 수 없습니다: {src}")

    zones: dict[tuple[int, str], list[list[int]]] = {(n, k): [] for n in (1, 2) for k in ("stop", "approach")}
    current = [1, "stop"]

    def on_click(event, x, y, *_):
        if event == cv2.EVENT_LBUTTONDOWN:
            zones[(current[0], current[1])].append([x, y])

    def dump() -> str:
        lines = []
        for n in (1, 2):
            if len(zones[(n, "stop")]) >= 3:
                z = {"line_num": n, "stop": zones[(n, "stop")]}
                if len(zones[(n, "approach")]) >= 3:
                    z["approach"] = zones[(n, "approach")]
                lines.append(z)
        return json.dumps({"lines": lines}, ensure_ascii=False)

    cv2.namedWindow("calibrate")
    cv2.setMouseCallback("calibrate", on_click)
    colors = {"stop": (0, 200, 0), "approach": (0, 200, 255)}
    while True:
        img = base.copy()
        for (n, kind), pts in zones.items():
            if pts:
                arr = np.array(pts, np.int32)
                cv2.polylines(img, [arr], len(pts) >= 3, colors[kind], 2)
                for p in pts:
                    cv2.circle(img, tuple(p), 4, colors[kind], -1)
                cv2.putText(img, f"L{n} {kind}", tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[kind], 2)
        cv2.putText(img, f"editing: LINE {current[0]} {current[1]}  (1/2, s/a, z undo, p print, q quit)",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow("calibrate", img)
        key = cv2.waitKey(30) & 0xFF
        if key == ord("1"):
            current[0] = 1
        elif key == ord("2"):
            current[0] = 2
        elif key == ord("s"):
            current[1] = "stop"
        elif key == ord("a"):
            current[1] = "approach"
        elif key == ord("z") and zones[(current[0], current[1])]:
            zones[(current[0], current[1])].pop()
        elif key == ord("p"):
            print(dump())
        elif key == ord("q"):
            break
    cv2.destroyAllWindows()
    print(dump())


if __name__ == "__main__":
    main()
