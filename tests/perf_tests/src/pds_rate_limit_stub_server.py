import json
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RATE_LIMIT_MESSAGE = "Mock PDS rate limit has been exceeded"


class LoadFriendlyThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 256


class FixedWindowRateLimiter:
    def __init__(
        self,
        average_limit: int,
        average_window_seconds: int,
        spike_limit: int,
        spike_window_seconds: int,
    ):
        self._started_at = time.time()
        self._windows = (
            ("average", average_limit * average_window_seconds, average_window_seconds),
            ("spike", spike_limit, spike_window_seconds),
        )
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}

    def check(self, scope: str) -> tuple[bool, str, int, int, int]:
        with self._lock:
            decision = None
            for name, limit, seconds in self._windows:
                # Anchor windows to server start so threshold behavior is stable across test runs.
                bucket = int((time.time() - self._started_at) // seconds)
                key = f"{scope}:{name}:{bucket}"
                count = self._counts.get(key, 0) + 1
                self._counts[key] = count
                decision = (count <= limit, name, count, limit, seconds)
                if not decision[0]:
                    break
            self._cleanup_old_buckets()
            return decision

    def _cleanup_old_buckets(self) -> None:
        now = int(time.time())
        keys_to_delete = []
        for key in self._counts:
            parts = key.rsplit(":", 2)
            if len(parts) != 3:
                continue
            _, window_name, bucket_str = parts
            seconds = next((w[2] for w in self._windows if w[0] == window_name), 1)
            bucket_start = int(bucket_str) * seconds
            if now - bucket_start > (seconds * 2):
                keys_to_delete.append(key)

        for key in keys_to_delete:
            self._counts.pop(key, None)


class MockPdsHandler(BaseHTTPRequestHandler):
    rate_limiter: FixedWindowRateLimiter
    protocol_version = "HTTP/1.1"

    def _write_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _write_empty_200(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def do_GET(self):
        if not self.path.startswith("/Patient/"):
            self._write_json(HTTPStatus.BAD_REQUEST, {"code": 400, "message": "Patient id is required"})
            return

        allowed, _, _, _, _ = self.rate_limiter.check("patient-lookup")
        if not allowed:
            self._write_json(HTTPStatus.TOO_MANY_REQUESTS, {"code": 429, "message": RATE_LIMIT_MESSAGE})
            return

        # Acceptance criteria: 200 with no response body below threshold.
        self._write_empty_200()

    def log_message(self, format: str, *args):
        return


def main() -> None:
    host = os.getenv("MOCK_PDS_BIND_HOST", "127.0.0.1")
    port = int(os.getenv("MOCK_PDS_BIND_PORT", "18080"))
    average_limit = int(os.getenv("MOCK_PDS_AVERAGE_LIMIT", "125"))
    average_window_seconds = int(os.getenv("MOCK_PDS_AVERAGE_WINDOW_SECONDS", "60"))
    spike_limit = int(os.getenv("MOCK_PDS_SPIKE_LIMIT", "450"))
    spike_window_seconds = int(os.getenv("MOCK_PDS_SPIKE_WINDOW_SECONDS", "1"))

    MockPdsHandler.rate_limiter = FixedWindowRateLimiter(
        average_limit=average_limit,
        average_window_seconds=average_window_seconds,
        spike_limit=spike_limit,
        spike_window_seconds=spike_window_seconds,
    )

    server = LoadFriendlyThreadingHTTPServer((host, port), MockPdsHandler)
    print(f"Mock PDS test server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
