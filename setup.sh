#!/usr/bin/env bash
# Robo_Shot 로컬 개발 환경 구축
#
# 사용법
#   ./setup.sh              db + backend + frontend + robot (vision 제외)
#   ./setup.sh backend      원하는 것만: db | backend | frontend | robot | vision
#   ./setup.sh all          vision까지 전부 (vision은 PyTorch 포함이라 수 GB 다운로드)
#
# .venv / node_modules / build 결과물은 git에 올리지 않는다. 각자 이 스크립트로 만든다.
# 다른 컴퓨터에서 복사된(경로가 안 맞는) .venv가 있으면 지우고 다시 만든다.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$ROOT/app"
DEFAULT_TARGETS=(db backend frontend robot)

# ROS2를 source한 터미널에서는 PYTHONPATH에 ROS 패키지가 섞여 venv/pytest가 꼬인다.
unset PYTHONPATH

log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m  ✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m  ! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m  ✗ %s\033[0m\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "'$1' 이(가) 필요합니다. $2"; }

copy_if_missing() {  # 예시 파일 → 실제 설정 파일 (이미 있으면 그대로 둔다)
  local example=$1 target=$2
  if [[ ! -f "$target" ]]; then
    cp "$example" "$target"
    ok "$(basename "$target") 생성 ($(basename "$example") 복사)"
  fi
}

# .venv가 이 위치에서 만들어진 것인지 확인한다. 다른 컴퓨터/경로에서 온 것이면 false.
venv_is_valid() {
  local venv=$1
  [[ -x "$venv/bin/python" ]] || return 1
  "$venv/bin/python" -c "import sys" >/dev/null 2>&1 || return 1
  head -n1 "$venv/bin/pip" 2>/dev/null | grep -qF "$venv/bin/python" || return 1
}

make_venv() {  # make_venv <디렉터리>  : <디렉터리>/.venv 를 만들고 requirements.txt 설치
  local dir=$1 venv="$1/.venv"
  need python3 "sudo apt install python3 python3-venv"
  if [[ -d "$venv" ]] && ! venv_is_valid "$venv"; then
    warn "$venv 는 다른 경로/컴퓨터에서 만들어진 것이라 다시 만듭니다."
    rm -rf "$venv"
  fi
  if [[ ! -d "$venv" ]]; then
    python3 -m venv "$venv" || die "venv 생성 실패. sudo apt install python3-venv 후 다시 실행하세요."
    ok ".venv 생성"
  fi
  "$venv/bin/python" -m pip install -q --upgrade pip
  "$venv/bin/python" -m pip install -q -r "$dir/requirements.txt"
  ok "requirements.txt 설치 ($("$venv/bin/python" --version))"
}

setup_db() {
  log "DB (MySQL, docker compose)"
  need docker "https://docs.docker.com/engine/install/ubuntu/"
  copy_if_missing "$APP/backend/.env.example" "$APP/backend/.env"
  (cd "$APP/backend" && docker compose up -d)
  printf '  MySQL 준비 대기'
  for _ in $(seq 1 60); do
    if [[ "$(docker inspect -f '{{.State.Health.Status}}' robo_shot_mysql 2>/dev/null)" == healthy ]]; then
      echo; ok "MySQL healthy (localhost:3306)"; return
    fi
    printf '.'; sleep 2
  done
  echo; die "MySQL이 준비되지 않았습니다: docker logs robo_shot_mysql"
}

setup_backend() {
  log "Backend (FastAPI)"
  make_venv "$APP/backend"
  copy_if_missing "$APP/backend/.env.example" "$APP/backend/.env"
}

setup_frontend() {
  log "Frontend (React + Vite)"
  need node "Node.js 18.18 이상: https://nodejs.org"
  need npm "Node.js와 함께 설치됩니다."
  local major; major=$(node -p 'process.versions.node.split(".")[0]')
  (( major >= 18 )) || die "Node.js 18 이상이 필요합니다 (현재 $(node -v))."
  (cd "$APP/frontend" && npm ci --no-audit --no-fund)
  ok "node_modules 설치 (package-lock.json 기준)"
  copy_if_missing "$APP/frontend/.env.example" "$APP/frontend/.env"
}

setup_robot() {
  log "Robot (ROS2 Jazzy, colcon)"
  if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
    warn "ROS2 Jazzy가 없어 건너뜁니다 (/opt/ros/jazzy). 로봇 노드를 실행할 PC에서만 필요합니다."
    return
  fi
  need colcon "sudo apt install python3-colcon-common-extensions"
  (
    set +u  # ROS setup 스크립트는 정의 안 된 변수를 쓴다
    # shellcheck disable=SC1091
    source /opt/ros/jazzy/setup.bash
    cd "$APP/robot" && colcon build --symlink-install
  )
  ok "colcon build (app/robot/install)"
}

setup_vision() {
  log "Vision (YOLO + OCR) — PyTorch 포함이라 오래 걸립니다"
  make_venv "$APP/vision"
  copy_if_missing "$APP/vision/config.example.json" "$APP/vision/config.json"
  [[ -f "$APP/vision/models/best.pt" ]] || warn "학습된 모델이 없습니다: app/vision/models/best.pt"
}

usage() {
  sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

main() {
  local targets=("$@")
  if [[ ${#targets[@]} -eq 0 ]]; then
    targets=("${DEFAULT_TARGETS[@]}")
  elif [[ "${targets[0]}" == all ]]; then
    targets=("${DEFAULT_TARGETS[@]}" vision)
  fi
  for t in "${targets[@]}"; do
    case "$t" in
      db|backend|frontend|robot|vision) "setup_$t" ;;
      -h|--help|help) usage; exit 0 ;;
      *) usage; die "알 수 없는 대상: $t" ;;
    esac
  done

  log "완료"
  cat <<'EOF'
  실행
    백엔드  : cd app/backend  && .venv/bin/uvicorn src.main:app --reload
    프론트  : cd app/frontend && npm run dev            (http://localhost:5173)
    로봇    : cd app/robot && source /opt/ros/jazzy/setup.bash && source install/setup.bash \
              && ros2 launch robo_shot_bridge robo_shot.launch.py
    비전    : cd app/vision && .venv/bin/python -m robo_shot_vision --config config.json --show
  테스트
    ./test.sh
EOF
}

# source 했을 때는 함수만 불러오고 실행하지 않는다 (테스트용)
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
