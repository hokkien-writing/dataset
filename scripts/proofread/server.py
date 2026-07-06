#!/usr/bin/env python3
"""Simple proofreading web server for OCR'd book markdown.

Serves a page-by-page side-by-side view of the scanned image (webp) alongside
the editable OCR markdown text delimited by `<!-- page:N -->` markers.

Usage:
    python3 scripts/proofread/server.py \
        --md books/004_Tie_Siann_Tsap_Ngou_Im.md \
        --pages tmp/004_Tie_Siann_Tsap_Ngou_Im/pages \
        [--port 8765] [--host 127.0.0.1]

Then open http://localhost:8765/ in your browser.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hmac
import json
import mimetypes
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PAGE_RE = re.compile(r"<!--\s*page:(\d+)\s*-->")
TEMPLATE_PATH = Path(__file__).resolve().parent / "ui.html"


class Book:
    def __init__(self, md_path: Path, pages_dir: Path | None, image_base_url: str | None = None) -> None:
        self.md_path = md_path
        self.pages_dir = pages_dir
        self.image_base_url = image_base_url.rstrip("/") if image_base_url else None
        self.lock = threading.Lock()
        self.preamble: str = ""
        self.pages: list[list] = []
        self.load()

    def load(self) -> None:
        text = self.md_path.read_text(encoding="utf-8")
        parts = PAGE_RE.split(text)
        self.preamble = parts[0]
        self.pages = []
        for i in range(1, len(parts), 2):
            pg = int(parts[i])
            body = parts[i + 1]
            if body.startswith("\n"):
                body = body[1:]
            self.pages.append([pg, body])

    def page_numbers(self) -> list[int]:
        return [pg for pg, _ in self.pages]

    def get_page(self, pg: int):
        for p, body in self.pages:
            if p == pg:
                return p, body
        return None

    def image_path(self, pg: int):
        if not self.pages_dir:
            return None
        for name in (f"{pg:04d}.webp", f"{pg:03d}.webp", f"{pg}.webp"):
            c = self.pages_dir / name
            if c.exists():
                return c
        return None

    def image_url(self, pg: int) -> str | None:
        if self.image_base_url:
            return f"{self.image_base_url}/{pg:04d}.webp"
        if self.image_path(pg):
            return f"/image/{pg}"
        return None

    def save_page(self, pg: int, new_body: str) -> bool:
        with self.lock:
            found = False
            for idx, (p, _) in enumerate(self.pages):
                if p == pg:
                    normalized = new_body.replace("\r\n", "\n").replace("\r", "\n")
                    if not normalized.endswith("\n"):
                        normalized += "\n"
                    self.pages[idx] = [p, normalized]
                    found = True
                    break
            if not found:
                return False
            chunks: list[str] = [self.preamble]
            for p, body in self.pages:
                chunks.append(f"<!-- page:{p} -->\n")
                chunks.append(body)
            self.md_path.write_text("".join(chunks), encoding="utf-8")
        return True


def build_handler(book: Book, html: str, auth_user: str | None, auth_pass: str | None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

        def _authorized(self) -> bool:
            if not auth_user or not auth_pass:
                return True
            header = self.headers.get("Authorization", "")
            if not header.startswith("Basic "):
                return False
            try:
                decoded = base64.b64decode(header[6:]).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError):
                return False
            user, sep, password = decoded.partition(":")
            if not sep:
                return False
            return hmac.compare_digest(user, auth_user) and hmac.compare_digest(password, auth_pass)

        def _unauthorized(self) -> None:
            body = b'{"error":"unauthorized"}'
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="proofread"')
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, payload) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _raw(self, status: int, body: bytes, content_type: str, cache: str = "no-store") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self._authorized():
                self._unauthorized()
                return
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                self._raw(200, html.encode("utf-8"), "text/html; charset=utf-8")
                return
            if path == "/api/pages":
                self._json(200, {"pages": book.page_numbers(), "md": str(book.md_path)})
                return
            m = re.match(r"^/api/page/(\d+)$", path)
            if m:
                pg = int(m.group(1))
                result = book.get_page(pg)
                if result is None:
                    self._json(404, {"error": f"page {pg} not found"})
                    return
                p, body = result
                self._json(200, {
                    "page": p,
                    "body": body,
                    "image_url": book.image_url(p),
                })
                return
            m = re.match(r"^/image/(\d+)$", path)
            if m:
                pg = int(m.group(1))
                img = book.image_path(pg)
                if img is None:
                    self._raw(404, b"not found", "text/plain")
                    return
                ctype, _ = mimetypes.guess_type(str(img))
                self._raw(200, img.read_bytes(), ctype or "image/webp", cache="public, max-age=3600")
                return
            self._raw(404, b"not found", "text/plain")

        def do_POST(self):
            if not self._authorized():
                self._unauthorized()
                return
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b""
            m = re.match(r"^/api/page/(\d+)$", path)
            if m:
                pg = int(m.group(1))
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except Exception as e:
                    self._json(400, {"error": f"bad JSON: {e}"})
                    return
                body = payload.get("body")
                if not isinstance(body, str):
                    self._json(400, {"error": "body must be string"})
                    return
                if not book.save_page(pg, body):
                    self._json(404, {"error": f"page {pg} not found"})
                    return
                self._json(200, {"ok": True, "page": pg})
                return
            self._raw(404, b"not found", "text/plain")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--md", required=True, type=Path, help="Markdown file with <!-- page:N --> markers")
    parser.add_argument("--pages", type=Path, default=None, help="Directory containing NNNN.webp page images")
    parser.add_argument("--image-base-url", default=None, help="Base URL for remote page images (NNNN.webp); used instead of --pages")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    md_path = args.md.resolve()
    if not md_path.exists():
        parser.error(f"markdown not found: {md_path}")
    pages_dir = args.pages.resolve() if args.pages else None
    if args.pages and not pages_dir.is_dir():
        parser.error(f"pages dir not found: {pages_dir}")
    if not pages_dir and not args.image_base_url:
        parser.error("must provide --pages or --image-base-url")
    if not TEMPLATE_PATH.exists():
        parser.error(f"UI template not found: {TEMPLATE_PATH}")

    auth_user = os.environ.get("PROOFREAD_USER") or None
    auth_pass = os.environ.get("PROOFREAD_PASSWORD") or None

    book = Book(md_path, pages_dir, args.image_base_url)
    html = TEMPLATE_PATH.read_text(encoding="utf-8").replace("__TITLE__", md_path.name)

    print(f"markdown: {md_path}")
    print(f"pages:    {pages_dir or '(remote)'}")
    if args.image_base_url:
        print(f"images:   {args.image_base_url} (remote)")
    print(f"pages found in md: {len(book.pages)}")
    print(f"auth:     {'enabled' if auth_user and auth_pass else 'disabled'}")
    print(f"serving on http://{args.host}:{args.port}/")

    handler = build_handler(book, html, auth_user, auth_pass)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
