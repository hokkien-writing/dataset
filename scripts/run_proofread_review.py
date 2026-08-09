#!/usr/bin/env python3
from __future__ import annotations

import argparse
import threading
import webbrowser
from pathlib import Path

from scripts.proofread_review.server import DocumentConfig, create_server


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = PROJECT_ROOT / "scripts/proofread_review/review_data.json"
DEFAULT_PDF = Path(
    "/Users/lim/Desktop/A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect.pdf"
)
DEFAULT_CACHE = PROJECT_ROOT / "tmp/proofread-review-pages"
DEFAULT_DECISIONS = PROJECT_ROOT / "tmp/007-proofread-decisions.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动 007 人工校订网页")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--page-field", default="page")
    parser.add_argument("--page-offset", type=int, default=0)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = DocumentConfig(
        pdf_path=args.pdf,
        page_field=args.page_field,
        page_offset=args.page_offset,
    )
    server = create_server(
        dataset_path=args.data,
        config=config,
        cache_dir=args.cache_dir,
        port=args.port,
        decisions_path=args.decisions,
    )
    url = f"http://127.0.0.1:{server.server_port}"
    if not args.no_open:
        threading.Timer(0.2, webbrowser.open, args=(url,)).start()
    print(f"007 人工校订网页：{url}")
    print("按 Ctrl-C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
