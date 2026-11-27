import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from robo_shot_vision.server_client import ServerClient, ServerError
from robo_shot_vision.stabilizer import Report


class FakeServer(BaseHTTPRequestHandler):
    calls: list = []

    def do_PUT(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n).decode("utf-8"))
        FakeServer.calls.append((self.path, body))
        if body["line_num"] == 3:
            code, res = 422, {"success": False, "message": "line_num: Input should be 1 or 2"}
        else:
            code, res = 200, {"success": True, "message": "created", "status": "ready"}
        data = json.dumps(res).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def client():
    FakeServer.calls = []
    httpd = HTTPServer(("127.0.0.1", 0), FakeServer)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield ServerClient(f"http://127.0.0.1:{httpd.server_port}")
    httpd.shutdown()


def test_visit_sends_put_car(client):
    res = client.visit(Report("12가3456", 1, True, "new"))
    assert res["status"] == "ready"
    assert FakeServer.calls == [("/car", {"car_num": "12가3456", "is_line": True, "line_num": 1})]


def test_visit_error_message(client):
    with pytest.raises(ServerError, match="Input should be 1 or 2"):
        client.visit(Report("12가3456", 3, True, "new"))


def test_visit_connection_error():
    with pytest.raises(ServerError, match="연결 실패"):
        ServerClient("http://127.0.0.1:1", timeout=0.5).visit(Report("12가3456", 1, True, "new"))
