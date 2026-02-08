from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


DEFAULT_INDEX_URL = (
    "https://www.bahai.org/library/authoritative-texts/the-universal-house-of-justice/messages/"
)
DEFAULT_OUTPUT_DIR = Path("data/samples/uhj_messages_md")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class MessageEntry:
    date: str
    title: str
    link: str
    message_id: str


class RateLimiter:
    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval_seconds = max(min_interval_seconds, 0.0)
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        if self._min_interval_seconds <= 0:
            return
        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed:
                time.sleep(self._next_allowed - now)
                now = time.monotonic()
            self._next_allowed = now + self._min_interval_seconds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape UHJ messages index and store markdown files with frontmatter."
    )
    parser.add_argument("--index-url", default=DEFAULT_INDEX_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-items", type=int, default=0, help="0 means all")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--delay-seconds", type=float, default=0.8)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def fetch_html(url: str, timeout_seconds: float, limiter: RateLimiter) -> str:
    limiter.wait()
    response = requests.get(
        url,
        timeout=timeout_seconds,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.text


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def infer_message_id(link: str) -> str:
    match = re.search(r"/messages/([^/]+)/", link)
    if match:
        return match.group(1)
    stem = re.sub(r"[^a-zA-Z0-9]+", "-", link).strip("-")
    return stem[:60] or "unknown"


def parse_index(index_html: str, index_url: str) -> list[MessageEntry]:
    soup = BeautifulSoup(index_html, "html.parser")
    entries: list[MessageEntry] = []
    seen_links: set[str] = set()

    for row in soup.select("table tr"):
        cells = row.select("td")
        if len(cells) < 2:
            continue
        date_text = normalize_space(cells[0].get_text(" ", strip=True))
        anchor = cells[1].find("a", href=True)
        if not anchor:
            continue
        title = normalize_space(anchor.get_text(" ", strip=True))
        full_link = urljoin(index_url, anchor["href"])
        if not full_link or full_link in seen_links:
            continue
        if "/messages/" not in full_link:
            continue
        seen_links.add(full_link)
        entries.append(
            MessageEntry(
                date=date_text,
                title=title,
                link=full_link,
                message_id=infer_message_id(full_link),
            )
        )

    if entries:
        return entries

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")
        if "/messages/" not in href:
            continue
        full_link = urljoin(index_url, href)
        if full_link in seen_links:
            continue
        seen_links.add(full_link)
        entries.append(
            MessageEntry(
                date="",
                title=normalize_space(anchor.get_text(" ", strip=True)),
                link=full_link,
                message_id=infer_message_id(full_link),
            )
        )
    return entries


def extract_page_text(page_html: str) -> tuple[str, str]:
    soup = BeautifulSoup(page_html, "html.parser")

    title = normalize_space(soup.title.get_text(" ", strip=True) if soup.title else "")
    title_node = soup.select_one("h1")
    if title_node:
        title = normalize_space(title_node.get_text(" ", strip=True)) or title

    selectors = [
        "#content",
        "article",
        "main",
        ".content",
        ".article-body",
        ".document-content",
        ".library-document",
    ]

    container = None
    for selector in selectors:
        candidate = soup.select_one(selector)
        if candidate:
            container = candidate
            break

    if container is None:
        container = soup.body or soup

    for bad in container.select("script,style,noscript,nav,footer,header,aside"):
        bad.decompose()

    raw_text = container.get_text("\n", strip=True)
    lines = [normalize_space(line) for line in raw_text.splitlines() if normalize_space(line)]
    noise_patterns = [
        re.compile(r"^hide note$", re.IGNORECASE),
        re.compile(r"^copy with reference$", re.IGNORECASE),
        re.compile(r"^copy link$", re.IGNORECASE),
        re.compile(r"^link$", re.IGNORECASE),
        re.compile(r"^note:$", re.IGNORECASE),
    ]
    filtered = [line for line in lines if not any(pat.match(line) for pat in noise_patterns)]
    text = "\n\n".join(filtered).strip()
    return title, text


def safe_frontmatter_value(value: str) -> str:
    escaped = (value or "").replace('"', '\\"')
    return f'"{escaped}"'


def markdown_for(entry: MessageEntry, page_title: str, body_text: str, source_url: str) -> str:
    content_sha = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    title = page_title or entry.title

    frontmatter = "\n".join(
        [
            "---",
            f"message_id: {safe_frontmatter_value(entry.message_id)}",
            f"date: {safe_frontmatter_value(entry.date)}",
            f"title: {safe_frontmatter_value(title)}",
            f"source_url: {safe_frontmatter_value(source_url)}",
            f"content_sha256: {safe_frontmatter_value(content_sha)}",
            f"scraped_at: {safe_frontmatter_value(generated_at)}",
            "---",
            "",
        ]
    )
    return frontmatter + body_text.strip() + "\n"


def existing_content_hash(markdown_path: Path) -> str | None:
    if not markdown_path.exists():
        return None
    text = markdown_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'^content_sha256:\s+"?([a-f0-9]{64})"?$', text, flags=re.MULTILINE)
    return match.group(1) if match else None


def output_path_for(entry: MessageEntry, output_dir: Path) -> Path:
    slug = entry.message_id.strip() or "unknown"
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", slug)
    return output_dir / f"{slug}.md"


def scrape_one(
    entry: MessageEntry,
    output_dir: Path,
    timeout_seconds: float,
    limiter: RateLimiter,
    dry_run: bool,
    overwrite: bool,
) -> dict:
    page_html = fetch_html(entry.link, timeout_seconds, limiter)
    page_title, body_text = extract_page_text(page_html)
    markdown = markdown_for(entry, page_title, body_text, entry.link)
    output_path = output_path_for(entry, output_dir)

    new_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
    old_hash = existing_content_hash(output_path)
    if old_hash == new_hash and not overwrite:
        return {"status": "skipped_duplicate", "id": entry.message_id, "path": str(output_path)}

    if dry_run:
        return {"status": "dry_run", "id": entry.message_id, "path": str(output_path)}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return {"status": "saved", "id": entry.message_id, "path": str(output_path)}


def bounded(entries: Iterable[MessageEntry], max_items: int) -> list[MessageEntry]:
    all_entries = list(entries)
    if max_items <= 0:
        return all_entries
    return all_entries[:max_items]


def main() -> None:
    args = parse_args()
    limiter = RateLimiter(args.delay_seconds)

    index_html = fetch_html(args.index_url, args.timeout_seconds, limiter)
    entries = parse_index(index_html, args.index_url)
    entries = bounded(entries, args.max_items)

    if not entries:
        raise SystemExit("No entries found on index page. Check selectors/index URL.")

    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(args.workers, 1)) as executor:
        future_map = {
            executor.submit(
                scrape_one,
                entry=entry,
                output_dir=args.output_dir,
                timeout_seconds=args.timeout_seconds,
                limiter=limiter,
                dry_run=args.dry_run,
                overwrite=args.overwrite,
            ): entry
            for entry in entries
        }
        for future in concurrent.futures.as_completed(future_map):
            entry = future_map[future]
            try:
                result = future.result()
                results.append(result)
                print(f"[{result['status']}] {entry.message_id} -> {result['path']}")
            except Exception as exc:  # noqa: BLE001
                err = {"status": "error", "id": entry.message_id, "error": str(exc)}
                results.append(err)
                print(f"[error] {entry.message_id}: {exc}")

    summary = {
        "index_url": args.index_url,
        "output_dir": str(args.output_dir),
        "count_total": len(entries),
        "count_saved": sum(1 for r in results if r.get("status") == "saved"),
        "count_skipped_duplicate": sum(1 for r in results if r.get("status") == "skipped_duplicate"),
        "count_dry_run": sum(1 for r in results if r.get("status") == "dry_run"),
        "count_error": sum(1 for r in results if r.get("status") == "error"),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
