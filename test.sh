#!/usr/bin/env bash
# Robo_Shot 전체 테스트
#
# 사용법
#   ./test.sh                  backend + frontend + vision + robot
#   ./test.sh backend vision   원하는 것만
#
# 먼저 ./setup.sh 로 환경을 만들어야 한다.
# vision / robot 테스트는 모델·ROS 없이 도는 순수 로직 테스트라 backend .venv의 pytest로 돌린다
# (vision .venv가 있으면 그걸 쓴다).

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$ROOT/app"
BACKEND_PY="$APP/backend/.venv/bin/python"

# ROS2 PYTHONPATH / pytest 플러그인이 섞이면 테스트가 엉뚱하게 실패한다.
unset PYTHONPATH
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

declare -A RESULT
FAILED=0

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

run() {  # run <이름> <디렉터리> <명령...>
  local name=$1 dir=$2; shift 2
  log "$name"
  if (cd "$dir" && "$@"); then
    RESULT[$name]="✓ passed"
  else
    RESULT[$name]="✗ FAILED"
    FAILED=1
  fi
}

need_backend_venv() {
  [[ -x "$BACKEND_PY" ]] || { echo "app/backend/.venv 가 없습니다. 먼저 ./setup.sh backend 를 실행하세요."; exit 1; }
}

test_backend() {
  need_backend_venv
  run backend "$APP/backend" "$BACKEND_PY" -m pytest -q -p asyncio -p no:cacheprovider
}

test_frontend() {
  [[ -d "$APP/frontend/node_modules" ]] || { echo "node_modules 가 없습니다. 먼저 ./setup.sh frontend"; RESULT[frontend]="✗ not set up"; FAILED=1; return; }
  run frontend "$APP/frontend" npm test --silent
}

test_vision() {
  local py="$APP/vision/.venv/bin/python"
  [[ -x "$py" ]] || { need_backend_venv; py=$BACKEND_PY; }
  run vision "$APP/vision" "$py" -m pytest -q -p no:cacheprovider
}

test_robot() {
  need_backend_venv
  run robot "$APP/robot/src/robo_shot_bridge" "$BACKEND_PY" -m pytest -q -p no:cacheprovider test
}

targets=("$@")
[[ ${#targets[@]} -eq 0 ]] && targets=(backend frontend vision robot)
for t in "${targets[@]}"; do
  case "$t" in
    backend|frontend|vision|robot) "test_$t" ;;
    *) echo "알 수 없는 대상: $t (backend | frontend | vision | robot)"; exit 2 ;;
  esac
done

log "결과"
for t in "${targets[@]}"; do printf '  %-9s %s\n' "$t" "${RESULT[$t]:-skipped}"; done
exit $FAILED
