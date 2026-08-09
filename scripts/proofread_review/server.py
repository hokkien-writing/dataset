from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from scripts.proofread_review.models import ReviewDataset, ReviewRecord, validate_decision_export


STATIC_DIR = Path(__file__).resolve().parent / "static"
_PAGE_PATH_RE = re.compile(r"^/api/page/([1-9][0-9]*)\.jpg$")
_STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


@dataclass(frozen=True)
class DocumentConfig:
    pdf_path: Path
    page_field: str = "page"
    page_offset: int = 0


class PageRenderer:
    def __init__(self, pdf_path: Path, cache_dir: Path) -> None:
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        if shutil.which("pdftoppm") is None or shutil.which("pdfinfo") is None:
            raise RuntimeError("Poppler commands pdfinfo and pdftoppm are required")
        self.pdf_path = pdf_path.resolve()
        self.cache_dir = cache_dir.resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        info = subprocess.run(
            ["pdfinfo", str(self.pdf_path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        pages = next(
            (line.split(":", 1)[1].strip() for line in info.splitlines() if line.startswith("Pages:")),
            "",
        )
        if not pages.isdigit():
            raise RuntimeError("Unable to read PDF page count")
        self.page_count = int(pages)

    def render(self, page: int) -> Path:
        if page < 1 or page > self.page_count:
            raise ValueError(f"PDF page must be between 1 and {self.page_count}")
        target = self.cache_dir / f"page-{page:04d}.jpg"
        if target.is_file() and target.stat().st_size:
            return target
        prefix = self.cache_dir / f".page-{page:04d}-{uuid.uuid4().hex}"
        produced = Path(f"{prefix}.jpg")
        try:
            subprocess.run(
                [
                    "pdftoppm",
                    "-f",
                    str(page),
                    "-l",
                    str(page),
                    "-singlefile",
                    "-jpeg",
                    "-r",
                    "180",
                    str(self.pdf_path),
                    str(prefix),
                ],
                check=True,
                capture_output=True,
            )
            if not produced.is_file() or not produced.stat().st_size:
                raise RuntimeError(f"PDF page {page} rendered no image")
            os.replace(produced, target)
        finally:
            produced.unlink(missing_ok=True)
        return target


class ReviewHTTPServer(ThreadingHTTPServer):
    dataset: dict[str, Any]
    config: DocumentConfig
    renderer: PageRenderer
    decisions_path: Path | None


def _apply_page_mapping(dataset: dict[str, Any], config: DocumentConfig) -> dict[str, Any]:
    result = dict(dataset)
    records = [dict(record) for record in dataset.get("records", [])]
    for record in records:
        record["pdf_page"] = int(record[config.page_field]) + config.page_offset
    result["records"] = records
    result["page_field"] = config.page_field
    result["page_offset"] = config.page_offset
    return result


def _handler_class() -> type[BaseHTTPRequestHandler]:
    class ReviewHandler(BaseHTTPRequestHandler):
        server: ReviewHTTPServer

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/api/health":
                self._send_json(
                    {
                        "status": "ok",
                        "record_count": self.server.dataset["record_count"],
                        "issue_count": self.server.dataset["issue_count"],
                        "pdf_pages": self.server.renderer.page_count,
                        "page_field": self.server.config.page_field,
                        "page_offset": self.server.config.page_offset,
                    }
                )
                return
            if path == "/api/data":
                self._send_json(self.server.dataset)
                return
            page_match = _PAGE_PATH_RE.fullmatch(path)
            if page_match:
                try:
                    image_path = self.server.renderer.render(int(page_match.group(1)))
                except ValueError as error:
                    self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                    return
                except (OSError, subprocess.SubprocessError, RuntimeError) as error:
                    self._send_json(
                        {"error": f"PDF page rendering failed: {error}"},
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                    )
                    return
                self._send_bytes(image_path.read_bytes(), "image/jpeg", cache=True)
                return
            static = _STATIC_FILES.get(path)
            if static:
                name, content_type = static
                file_path = STATIC_DIR / name
                if file_path.is_file():
                    self._send_bytes(file_path.read_bytes(), content_type)
                    return
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/api/decisions" or self.server.decisions_path is None:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 5_000_000:
                    raise ValueError("invalid decision payload size")
                payload = json.loads(self.rfile.read(length))
                dataset = ReviewDataset.from_records([
                    ReviewRecord.from_dict(record) for record in self.server.dataset["records"]
                ])
                normalized = validate_decision_export(dataset, payload)
                output = {**payload, "data_version": dataset.data_version, "decisions": normalized}
                target = self.server.decisions_path
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
                temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                os.replace(temporary, target)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"saved": len(normalized)})

        def _send_json(
            self, value: object, status: HTTPStatus = HTTPStatus.OK
        ) -> None:
            self._send_bytes(
                json.dumps(value, ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
                status,
            )

        def _send_bytes(
            self,
            value: bytes,
            content_type: str,
            status: HTTPStatus = HTTPStatus.OK,
            cache: bool = False,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(value)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "public, max-age=86400" if cache else "no-store")
            self.end_headers()
            self.wfile.write(value)

        def log_message(self, format: str, *args: object) -> None:
            return

    return ReviewHandler


def create_server(
    dataset_path: Path,
    config: DocumentConfig,
    cache_dir: Path,
    host: str = "127.0.0.1",
    port: int = 0,
    decisions_path: Path | None = None,
) -> ReviewHTTPServer:
    if host != "127.0.0.1":
        raise ValueError("review server must bind to 127.0.0.1")
    if not isinstance(config.page_offset, int) or isinstance(config.page_offset, bool):
        raise ValueError("page offset must be an integer")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if (
        dataset.get("schema") != "proofread-review-data/v1"
        or dataset.get("record_count") != len(dataset.get("records", []))
    ):
        raise ValueError("invalid review dataset")
    records = dataset.get("records", [])
    if not records or any(config.page_field not in record for record in records):
        raise ValueError(
            f"page field {config.page_field!r} is unavailable in dataset records"
        )
    server = ReviewHTTPServer((host, port), _handler_class())
    server.config = config
    server.dataset = _apply_page_mapping(dataset, config)
    server.renderer = PageRenderer(config.pdf_path, cache_dir)
    server.decisions_path = decisions_path.resolve() if decisions_path else None
    return server
