import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import openpyxl


SOURCE_DIR = Path(__file__).resolve().parent
SOURCE = SOURCE_DIR / "si_mod6.xlsx"
PIPELINE_DIR = SOURCE_DIR.parent
DEFAULT_SHEET = "COM"


def clean_url(url):
    cleaned = str(url).strip()
    cleaned = re.sub(r"\s+e\s+(?=[A-Za-z_]+=)", "&", cleaned)
    if cleaned.count("?") > 1:
        first, rest = cleaned.split("?", 1)
        cleaned = first + "?" + rest.replace("?", "&")
    return cleaned


def is_book(url, resource_code):
    parsed = urlparse(url)
    return "sophia.com.br" in parsed.netloc.lower() or bool(resource_code)


def is_video(url, title):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    title_l = (title or "").lower()
    return (
        any(domain in host for domain in ("youtube.com", "youtu.be", "vimeo.com", "ted.com"))
        or "video" in title_l
        or "vídeo" in title_l
        or "videoaula" in title_l
    )


def make_record(row_number, data):
    return {
        "id": row_number,
        "title": data.get("Title"),
        "url": clean_url(data.get("URL")),
        "description": data.get("Description") or "",
    }


def make_book_record(row_number, data):
    return {
        "id": row_number,
        "title": data.get("Title"),
        "resource_code": data.get("Resource code"),
        "description": data.get("Description") or "",
        "url": clean_url(data.get("URL")),
    }


def export_links(*, workbook_path: Path, sheet_name: str, output_root: Path):
    workbook = openpyxl.load_workbook(workbook_path, data_only=True)
    worksheet = workbook[sheet_name]
    headers = [cell.value for cell in worksheet[1]]

    exports = {"articles": [], "books": [], "videos": []}
    for row_number, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
        data = dict(zip(headers, row))
        if data.get("Type") != "Self-study":
            continue

        url = clean_url(data.get("URL"))
        resource_code = data.get("Resource code")
        if not url and not resource_code:
            continue

        if is_book(url, data.get("Resource code")):
            exports["books"].append(make_book_record(row_number, data))
            continue

        if not url:
            continue

        record = make_record(row_number, data)
        if is_video(record["url"], record.get("title")):
            exports["videos"].append(record)
        else:
            exports["articles"].append(record)

    output_paths = {
        "articles": output_root / "article_url.json",
        "books": output_root / "book_url.json",
        "videos": output_root / "video_url.json",
    }
    for key, path in output_paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(exports[key], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return {
        key: {"count": len(exports[key]), "path": str(output_paths[key])}
        for key in exports
    }


def export_com_links():
    return export_links(
        workbook_path=SOURCE,
        sheet_name=DEFAULT_SHEET,
        output_root=PIPELINE_DIR / "source",
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Export workbook self-study links by source type.")
    parser.add_argument("--workbook", type=Path, default=SOURCE)
    parser.add_argument("--sheet", default=DEFAULT_SHEET)
    parser.add_argument("--output-root", type=Path, default=PIPELINE_DIR / "source")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    summary = export_links(
        workbook_path=args.workbook.resolve(),
        sheet_name=args.sheet,
        output_root=args.output_root.resolve(),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("total", sum(item["count"] for item in summary.values()))
