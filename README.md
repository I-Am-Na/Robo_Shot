# Robo_Shot

지능형 주유로봇 **Robo_Shot**의 Repository입니다.

컴퓨터 비전으로 차량과 번호판을 인식하고, 음성으로 주문을 받은 뒤, 두산 로봇팔이 주유를 하는 **무인 주유소** 시스템입니다.

<p>
  <img src="https://img.shields.io/badge/Doosan_Robotics-0055A4?style=flat-square&logoColor=white" alt="Doosan Robotics" />
  <img src="https://img.shields.io/badge/ROS2-22314E?style=flat-square&logo=ros&logoColor=white" alt="ROS2" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/YOLO-111F68?style=flat-square&logo=ultralytics&logoColor=white" alt="YOLO" />
  <img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=flat-square&logo=opencv&logoColor=white" alt="OpenCV" />
  <img src="https://img.shields.io/badge/Ubuntu-E95420?style=flat-square&logo=ubuntu&logoColor=white" alt="Ubuntu" />
</p>

## 기술 스택

| 분야 | 기술 |
|---|---|
| 로봇 | <img src="https://img.shields.io/badge/Doosan_Robotics-0055A4?style=flat-square&logoColor=white" alt="Doosan Robotics" /> <img src="https://img.shields.io/badge/ROS2-22314E?style=flat-square&logo=ros&logoColor=white" alt="ROS2" /> |
| 컴퓨터 비전 | <img src="https://img.shields.io/badge/YOLO-111F68?style=flat-square&logo=ultralytics&logoColor=white" alt="YOLO" /> <img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=flat-square&logo=opencv&logoColor=white" alt="OpenCV" /> |
| 음성 · AI | <img src="https://img.shields.io/badge/STT-6E40C9?style=flat-square" alt="STT" /> <img src="https://img.shields.io/badge/TTS-6E40C9?style=flat-square" alt="TTS" /> <img src="https://img.shields.io/badge/AI_Agent-412991?style=flat-square" alt="AI Agent" /> |
| 서버 · DB | <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" /> <img src="https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite" /> (예정) |
| 언어 · 환경 | <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" /> <img src="https://img.shields.io/badge/Ubuntu-E95420?style=flat-square&logo=ubuntu&logoColor=white" alt="Ubuntu" /> |

---

## 시스템 흐름

```
 Vehicle Detection      관제 카메라 영상에서 YOLO로 정지선 진입을 감지하고 번호판을 인식
        │
        ▼
 Vehicle Identification 번호판으로 차량 이력을 조회하여 신규 차량은 등록하고,
        │               재방문 차량은 저장된 유종 정보를 불러옴
        ▼
 Session Dispatch       주유 세션을 생성하고 주유 로봇에 차량·유종 정보를 전달
        │
        ▼
 Voice Ordering         STT로 고객의 음성 주문을 수신  (예: "5만원 넣어주세요")
        │
        ▼
 Order Confirmation     AI Agent가 주문 내용을 복창하고 고객의 승인 여부를 확인
        │               (예: "휘발유 5만원 주유하겠습니다" → 네 / 아니오)
        ▼
 Fueling Operation      주유구 커버 개방 → 주유캡 개방·거치 → 노즐 파지 → 노즐 삽입 → 주유
        │
        ▼
 Completion             주유 완료 신호 수신 → 노즐 회수·거치 → 주유캡·커버 체결
                        → TTS로 완료 안내
```

> 재방문 차량은 DB에 저장된 유종 정보를 활용하여 유종 확인 절차를 생략합니다.

## 팀 구성 및 역할

| 역할 | 담당 | 주요 업무 |
|---|---|---|
| **Vision Engineer** | 희범 | 관제 카메라 기반 차량 진입 감지, YOLO 번호판 인식(ANPR) |
| **Backend & Communication Engineer** | 병옥, 세웅 | 통신 노드 설계, 웹서버·DB(CRUD) 구축, 주유 세션 관리, 모듈 간 이벤트 중계, STT 음성 주문 수신 |
| **AI Agent Engineer** | 연수 | 음성 주문 의도 분석, 주문 복창 및 고객 승인 확인 대화 |
| **Robot Motion Engineer** | 규진 | 두산 로봇팔 주유 동작 시퀀스 설계·제어, 주유 완료 처리, TTS 완료 안내 |

---



### 차량 진입부터 저장까지

```
[관제캠 + YOLO]
   │  진입 이벤트 { pump_id, plate, confidence, detected_at }
   ▼
[웹서버]
   1. 검증       신뢰도 기준 미달이면 무시, 해당 주유기에 진행 중인 세션이 있으면 무시
   2. 차량 조회   번호판 형식 정규화 후 vehicles에서 검색
                  ├─ 있음 → 재방문: 저장된 유종 사용
                  └─ 없음 → 신규: 차량 등록 (유종은 비워 둠)
   3. 세션 생성   fueling_sessions 추가 (상태: 차량감지)
   4. 이력 기록   session_events에 VEHICLE_DETECTED 추가
                  (2~4는 하나의 트랜잭션으로 처리)
   ▼
[주유봇 알림]  { session_id, fuel_type }   ※ 신규 차량은 fuel_type = null
```

- YOLO는 매 프레임 결과를 보내므로, **주유기당 진행 중인 세션은 하나**로 제한해 중복 인식을 걸러냅니다.
- **유종은 주문이 확인된 뒤에 저장합니다.** 고객이 "네"라고 답한 시점에 `vehicles.fuel_type`을 기록하며, 확인되지 않은 유종은 저장하지 않습니다.

### 데이터베이스 테이블

| 테이블 | 용도 | 주요 칼럼 |
|---|---|---|
| `vehicles` | 차량 정보 | id, plate, fuel_type(nullable), created_at, last_visit_at |
| `pumps` | 주유기·로봇 연결 | id, name, robot_id, fuel_types |
| `fueling_sessions` | 주유 한 건의 진행 상태 | id, vehicle_id, pump_id, state, started_at, ended_at |
| `orders` | 주문 내용 | id, session_id, fuel_type, amount, confirmed, created_at |
| `session_events` | 상태 변경·오류 이력 | id, session_id, event_type, payload, created_at |

### 세션 상태

```
차량감지 → 주문대기 → 확인대기 → 주유중 → 완료
                         │  "아니오"
                         └──────→ 주문대기 (다시 주문 받기)

어느 단계에서든 → 취소 / 오류
```

### 안전 · 개인정보

- **번호판 오인식에 대비합니다.** 재방문 차량이어도 확인 멘트에 유종을 포함해("**휘발유** 5만원 주유하겠습니다") 고객이 바로잡을 수 있게 합니다.
- **번호판은 개인정보입니다.** 로그에는 `12가****`처럼 가려서 남기고 원본은 DB에만 저장합니다. 접근 권한과 보관 기간은 팀에서 정합니다.

---

## 미정 사항

- [ ] 파트 간 통신 방식 (ROS2 토픽·서비스 / HTTP / 혼합)
- [ ] 각 이벤트의 메시지 형식
- [ ] 번호판 인식 신뢰도 기준값
- [ ] 번호판 데이터 접근 권한·보관 기간
- [ ] 결제 처리 여부 (현재는 금액만 기록)
