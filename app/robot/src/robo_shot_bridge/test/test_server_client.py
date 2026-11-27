import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote

import pytest

from robo_shot_bridge.server_client import ServerClient, ServerError


class FakeServer(BaseHTTPRequestHandler):
    calls: list = []
    task = {"success": True, "message": "start", "start": True, "car_num": "11가1111",
            "line_num": 1, "fuel_type": "휘발유", "amount": 50000}

    def _send(self, code, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        FakeServer.calls.append(("GET", unquote(self.path)))
        self._send(200, FakeServer.task)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else None

    def do_POST(self):
        FakeServer.calls.append(("POST", unquote(self.path), self._body()))
        self._send(201, {"success": True, "message": "created", "action": {"id": 7}})

    def do_PUT(self):
        body = self._body()
        if self.path.startswith("/robot/actions/"):
            FakeServer.calls.append(("PUT", unquote(self.path), body))
            self._send(200, {"success": True, "message": "updated"})
            return
        FakeServer.calls.append(("PUT", unquote(self.path)))
        if "99하9999" in unquote(self.path):
            self._send(404, {"success": False, "message": "car not found: 99하9999"})
        else:
            self._send(200, {"success": True, "message": "fueling completed", "next_car_num": "22나2222"})

    def log_message(self, *args):
        pass


@pytest.fixture
def client():
    FakeServer.calls = []
    httpd = HTTPServer(("127.0.0.1", 0), FakeServer)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield ServerClient(f"http://127.0.0.1:{httpd.server_port}")
    httpd.shutdown()


def test_get_task(client):
    task = client.get_task()
    assert (task.start, task.car_num, task.line_num, task.fuel_type, task.amount) == (
        True, "11가1111", 1, "휘발유", 50000,
    )


def test_complete_encodes_korean_car_num(client):
    assert client.complete("11가1111") == "22나2222"
    assert FakeServer.calls[-1] == ("PUT", "/car/11가1111/complete")


def test_http_error_raises_with_message(client):
    with pytest.raises(ServerError, match="car not found"):
        client.complete("99하9999")


def test_connection_error_raises():
    with pytest.raises(ServerError, match="연결 실패"):
        ServerClient("http://127.0.0.1:1", timeout=0.5).get_task()


def test_create_and_update_action(client):
    from robo_shot_bridge.server_client import RobotTask

    task = RobotTask(start=True, car_num="11가1111", line_num=1, fuel_type="휘발유", amount=50000)
    assert client.create_action(task) == 7
    assert FakeServer.calls[-1] == ("POST", "/robot/actions",
                                    {"car_num": "11가1111", "line_num": 1, "fuel_type": "휘발유", "amount": 50000})

    client.update_action(7, "running", step="노즐 삽입", step_index=4, step_count=7)
    assert FakeServer.calls[-1] == ("PUT", "/robot/actions/7",
                                    {"status": "running", "step": "노즐 삽입", "step_index": 4, "step_count": 7})

    client.update_action(7, "failed", message="gripper error")
    assert FakeServer.calls[-1] == ("PUT", "/robot/actions/7", {"status": "failed", "message": "gripper error"})
