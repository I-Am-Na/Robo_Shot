"""FastAPI 서버 HTTP 클라이언트. 표준 라이브러리(urllib)만 사용한다."""

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class RobotTask:
    """GET /robot/task 응답."""

    start: bool
    car_num: str | None = None
    line_num: int | None = None
    fuel_type: str | None = None
    amount: int | None = None


class ServerError(Exception):
    pass


class ServerClient:
    def __init__(self, base_url: str, timeout: float = 2.0):
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        req = urllib.request.Request(f"{self._base}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as res:
                result = json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                message = json.loads(e.read().decode("utf-8")).get("message", str(e))
            except (ValueError, AttributeError):
                message = str(e)
            raise ServerError(f"{method} {path} -> {e.code}: {message}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ServerError(f"{method} {path} 연결 실패: {e}") from e
        if not result.get("success"):
            raise ServerError(f"{method} {path} 실패: {result.get('message')}")
        return result

    def get_task(self) -> RobotTask:
        """결제가 끝나 주유를 시작해야 하는 차량이 있으면 start=True."""
        body = self._request("GET", "/robot/task")
        return RobotTask(
            start=bool(body.get("start")),
            car_num=body.get("car_num"),
            line_num=body.get("line_num"),
            fuel_type=body.get("fuel_type"),
            amount=body.get("amount"),
        )

    def complete(self, car_num: str) -> str | None:
        """주유 완료 보고. 이어서 ready가 된 다음 차량번호를 돌려준다."""
        body = self._request("PUT", f"/car/{urllib.parse.quote(car_num)}/complete")
        return body.get("next_car_num")

    # --- 로봇 실행 기록 (robot_action) ---

    def create_action(self, task: RobotTask) -> int:
        """주유 goal을 보낼 때 기록 생성. 기록 id를 돌려준다."""
        body = self._request("POST", "/robot/actions", {
            "car_num": task.car_num,
            "line_num": task.line_num,
            "fuel_type": task.fuel_type,
            "amount": task.amount,
        })
        return int(body["action"]["id"])

    def update_action(
        self,
        action_id: int,
        status: str,
        step: str | None = None,
        step_index: int | None = None,
        step_count: int | None = None,
        message: str | None = None,
    ) -> None:
        """status: running | succeeded | failed | canceled | rejected"""
        payload = {"status": status}
        for key, value in (("step", step), ("step_index", step_index), ("step_count", step_count),
                           ("message", message)):
            if value is not None:
                payload[key] = value
        self._request("PUT", f"/robot/actions/{action_id}", payload)
