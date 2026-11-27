# Robo_Shot Vision

관제 카메라 영상에서 차량·번호판을 찾아 라인 진입을 판단하고 서버에 `PUT /car`를 보냅니다.

```
카메라 프레임 → YOLO(번호판·차량 위치) → OCR(번호판 글자) → 형식 보정(12가3456)
            → 라인 구역 판단(정지 구역=is_line true / 진입 구역=false)
            → 여러 프레임 확정 → PUT /car (처음·상태 변경 시, 같은 상태면 30초마다)
```

## 학습이 끝나면 할 일

1. 설치
   ```bash
   cd app/vision
   python3 -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   ```
2. 모델 넣기: `models/best.pt`
3. 설정 만들기: `cp config.example.json config.json`
   - `plate_classes`: 모델의 번호판 클래스 이름 (예: `["plate"]`)
   - `vehicle_classes`: 차량 클래스 이름. 차량을 학습하지 않았으면 그대로 둬도 됩니다 (번호판 박스로 판단).
   - `min_det_conf`: 번호판 인식 신뢰도 기준값
4. 라인 구역 찍기: 카메라 화면에서 1번·2번 라인의 정지 구역/진입 구역을 클릭
   ```bash
   python -m robo_shot_vision.calibrate --source 0
   ```
   출력된 `{"lines": [...]}`를 `config.json`의 `lines`에 붙여 넣습니다.
5. 서버 없이 확인
   ```bash
   python -m robo_shot_vision --config config.json --show --dry-run
   ```
6. 실제 실행 (백엔드가 떠 있어야 함)
   ```bash
   python -m robo_shot_vision --config config.json --show
   ```
   `--source` 로 웹캠 번호, 영상 파일(`test.mp4`), `rtsp://...` 를 바꿀 수 있습니다.

## 파일

| 파일 | 내용 |
|---|---|
| `yolo_detector.py` | YOLO 모델 → 번호판·차량 박스 (모델 교체 지점) |
| `ocr_reader.py` | 번호판 이미지 → 글자, EasyOCR (OCR 교체 지점) |
| `plate.py` | OCR 결과 보정·형식 검사 (`I2가34S6` → `12가3456`) |
| `geometry.py` | 라인 구역 판단 (차량 박스 아래 가운데 기준) |
| `stabilizer.py` | 프레임 확정·전송 횟수 조절 |
| `pipeline.py` | 위 단계 연결 |
| `__main__.py` | 카메라 루프, 화면 표시 |
| `calibrate.py` | 라인 구역 찍기 도구 |

## 테스트 (모델 없이 돌아감)

```bash
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```
ROS2 환경이 섞이면 pytest가 실패하므로 `env -u PYTHONPATH`를 붙입니다.
