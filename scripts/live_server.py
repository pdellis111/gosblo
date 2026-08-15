#!/usr/bin/env python3
import argparse
import os
import posixpath
import time
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


RELOAD_SNIPPET = b"""
<script>
(() => {
  const events = new EventSource('/__live_reload');
  events.addEventListener('reload', () => location.reload());
})();
</script>
"""


class LiveReloadHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        self.site_directory = Path(directory).resolve()
        super().__init__(*args, directory=str(self.site_directory), **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path == "/__live_reload":
            self.stream_reload_events()
            return
        super().do_GET()

    def end_headers(self):
        if self.path.endswith((".html", "/")):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            for index in ("index.html", "index.htm"):
                index_path = os.path.join(path, index)
                if os.path.isfile(index_path):
                    path = index_path
                    break

        if not path.endswith((".html", ".htm")) or not os.path.isfile(path):
            return super().send_head()

        try:
            body = Path(path).read_bytes()
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        lower_body = body.lower()
        insert_at = lower_body.rfind(b"</body>")
        if insert_at == -1:
            body += RELOAD_SNIPPET
        else:
            body = body[:insert_at] + RELOAD_SNIPPET + body[insert_at:]

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return BytesResponse(body)

    def stream_reload_events(self):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        last_seen = newest_mtime(self.site_directory)
        while True:
            time.sleep(0.5)
            current = newest_mtime(self.site_directory)
            if current > last_seen:
                last_seen = current
                try:
                    self.wfile.write(b"event: reload\ndata: changed\n\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return

    def translate_path(self, path):
        path = urlsplit(path).path
        path = posixpath.normpath(unquote(path))
        words = [part for part in path.split("/") if part]
        resolved = self.site_directory
        for word in words:
            if word in (os.curdir, os.pardir):
                continue
            resolved = resolved / word
        return str(resolved)


class BytesResponse:
    def __init__(self, body):
        self.body = body

    def read(self, _size=-1):
        body = self.body
        self.body = b""
        return body

    def close(self):
        pass


class LiveReloadServer(ThreadingHTTPServer):
    allow_reuse_address = True


def newest_mtime(directory):
    newest = 0
    for path in directory.rglob("*"):
        if path.is_file():
            try:
                newest = max(newest, path.stat().st_mtime_ns)
            except OSError:
                pass
    return newest


def main():
    parser = argparse.ArgumentParser(description="Serve static files with browser reloads.")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--directory", default="site")
    args = parser.parse_args()

    handler = partial(LiveReloadHandler, directory=args.directory)
    with LiveReloadServer(("", args.port), handler) as server:
        print(f"Serving {args.directory} at http://localhost:{args.port}")
        print("Browser refreshes automatically when files change.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
