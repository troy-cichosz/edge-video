import json
import mimetypes
import threading
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import urlparse


class HealthServer:
    def __init__(self, config, state):
        self.config = config
        self.state = state
        self.live_root = config.live_root

        self.server = ThreadingHTTPServer(
            (
                config.health_host,
                config.health_port,
            ),
            self._handler(),
        )

        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )

    def _handler(self):
        state = self.state
        live_root = self.live_root

        class Handler(BaseHTTPRequestHandler):

            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path

                if path in ("/health", "/status"):
                    self._json_status(state())
                    return

                if path == "/stream":
                    self.send_response(302)
                    self.send_header(
                        "Location",
                        "/stream/index.m3u8",
                    )
                    self.end_headers()
                    return

                if path.startswith("/stream/"):
                    self._serve_stream(
                        path,
                        live_root,
                    )
                    return

                self.send_response(404)
                self.end_headers()

            def _json_status(self, payload):
                data = json.dumps(
                    payload
                ).encode("utf-8")

                self.send_response(
                    200
                    if payload.get("status") == "ok"
                    else 503
                )

                self.send_header(
                    "Content-Type",
                    "application/json",
                )

                self.send_header(
                    "Content-Length",
                    str(len(data)),
                )

                self.end_headers()
                self.wfile.write(data)

            def _serve_stream(self, request_path, root):
                relative = request_path[
                    len("/stream/")
                :]

                if not relative:
                    relative = "index.m3u8"

                requested = (
                    root / relative
                ).resolve()

                root_resolved = root.resolve()

                try:
                    requested.relative_to(
                        root_resolved
                    )
                except ValueError:
                    self.send_response(403)
                    self.end_headers()
                    return

                if not requested.is_file():
                    self.send_response(404)
                    self.end_headers()
                    return

                if requested.suffix == ".m3u8":
                    content_type = (
                        "application/vnd.apple.mpegurl"
                    )
                elif requested.suffix == ".ts":
                    content_type = "video/mp2t"
                else:
                    content_type = (
                        mimetypes.guess_type(
                            str(requested)
                        )[0]
                        or "application/octet-stream"
                    )

                try:
                    data = requested.read_bytes()
                except OSError:
                    self.send_response(404)
                    self.end_headers()
                    return

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    content_type,
                )

                self.send_header(
                    "Content-Length",
                    str(len(data)),
                )

                # Do not let clients cache a live playlist.
                if requested.suffix == ".m3u8":
                    self.send_header(
                        "Cache-Control",
                        "no-cache, no-store, must-revalidate",
                    )
                else:
                    self.send_header(
                        "Cache-Control",
                        "no-cache",
                    )

                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *_args):
                return

        return Handler

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()