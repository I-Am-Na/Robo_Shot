"""FastAPI 서버 PUT /car 호출. 표준 라이브러리(urllib)만 사용."""

import json
import urllib.error
import urllib.request

from robo_shot_vision.stabilizer import Report


class ServerError(Exception):
    pass


class ServerClient:
    def __init__(self, base_url: str, timeout: float = 2.0):
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def visit(self, report: Report) -> dict:
        """PUT /car. 서버 응답(success, message, status)을 돌려준다."""
        body = json.dumps(
            {"car_num": report.car_num, "is_line": report.is_line, "line_num": report.line_num}
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base}/car", data=body, headers={"Content-Type": "application/json"}, method="PUT"
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as res:
                result = json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                message = json.loads(e.read().decode("utf-8")).get("message", str(e))
            except (ValueError, AttributeError):
                message = str(e)
            raise ServerError(f"PUT /car -> {e.code}: {message}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ServerError(f"PUT /car 연결 실패: {e}") from e
        if not result.get("success"):
            raise ServerError(f"PUT /car 실패: {result.get('message')}")
        return result
