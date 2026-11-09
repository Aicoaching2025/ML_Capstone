"""Shared, resumable downloader with provenance for Step 7 (full-history acquisition).

- Small per-file downloads only (no bulk archives).
- Skips files already present and valid, so reruns download nothing new.
- Resumes partial downloads (HTTP Range) and retries with backoff on server errors.
- Writes a .download.json sidecar and one row per file in data/manifests/downloads.csv.
"""
from __future__ import annotations

import csv
import hashlib
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httpx

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/manifests/downloads.csv"
FIELDS = ["source_url", "retrieved_at_utc", "local_filename", "file_hash_sha256", "source_product",
          "requested_period", "station_or_zone", "provider", "model", "notes"]
RETRY_STATUS = {429, 500, 502, 503, 504}


class NotFound(Exception):
    """The provider returned 404 for this URL (not retried)."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def valid_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            return z.testzip() is None and len(z.namelist()) > 0
    except zipfile.BadZipFile:
        return False


def valid_lcd_csv(path: Path) -> bool:
    with path.open(encoding="utf-8", errors="replace") as f:
        return f.readline().startswith('"STATION"') and path.stat().st_size > 1_000_000


def valid_openmeteo_json(path: Path) -> bool:
    try:
        data = json.loads(path.read_text())
    except ValueError:
        return False
    return "error" not in data and "hourly" in data and len(data["hourly"].get("time", [])) > 0


def fetch(url: str, dest: Path, validate: Callable[[Path], bool], tries: int = 6,
          timeout: float = 120.0, resumable: bool = True) -> dict:
    """Download url to dest unless a valid copy exists. Returns the sidecar metadata."""
    sidecar = dest.with_name(dest.name + ".download.json")
    legacy_sidecar = dest.with_suffix(".download.json")  # pilot-era naming
    if dest.exists() and validate(dest):
        for s in (sidecar, legacy_sidecar):
            if s.exists():
                return {**json.loads(s.read_text()), "skipped": True}
        meta = {"source_url": url, "retrieved_at_utc": datetime.fromtimestamp(dest.stat().st_mtime, timezone.utc).isoformat(),
                "note": "pre-existing file; retrieval time taken from file modification time"}
        sidecar.write_text(json.dumps(meta, indent=2) + "\n")
        return {**meta, "skipped": True}
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    last_error = None
    for attempt in range(tries):
        have = part.stat().st_size if (resumable and part.exists()) else 0
        headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                with client.stream("GET", url, headers=headers) as r:
                    if r.status_code == 404:
                        raise NotFound(url)
                    if r.status_code == 416:  # part already complete
                        pass
                    elif r.status_code in RETRY_STATUS:
                        raise httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
                    else:
                        r.raise_for_status()
                        mode = "ab" if (have and r.status_code == 206) else "wb"
                        with part.open(mode) as f:
                            for chunk in r.iter_bytes(1 << 20):
                                f.write(chunk)
                    headers_out = {"http_last_modified": r.headers.get("last-modified"),
                                   "http_etag": r.headers.get("etag")}
            if not validate(part):
                part.unlink(missing_ok=True)
                raise ValueError(f"downloaded file failed validation: {url}")
            part.rename(dest)
            meta = {"source_url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                    **headers_out, "bytes": dest.stat().st_size, "skipped": False}
            sidecar.write_text(json.dumps({k: v for k, v in meta.items() if k not in ("skipped",)}, indent=2) + "\n")
            return meta
        except NotFound:
            raise
        except (httpx.HTTPError, ValueError, OSError) as e:
            last_error = e
            wait = min(5 * 2 ** attempt, 120)
            print(f"    retry {attempt + 1}/{tries} in {wait}s: {e}")
            time.sleep(wait)
    raise RuntimeError(f"giving up on {url}: {last_error}")


def read_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    with MANIFEST.open(newline="") as f:
        return list(csv.DictReader(f))


def record(path: Path, meta: dict, **fields) -> None:
    """Add one manifest row for path unless an identical (file, hash) row already exists."""
    rel = str(path.resolve().relative_to(ROOT))
    digest = sha256(path)
    rows = read_manifest()
    if any(r["local_filename"] == rel and r["file_hash_sha256"] == digest for r in rows):
        return
    row = {k: "" for k in FIELDS}
    row.update({"source_url": meta["source_url"], "retrieved_at_utc": meta["retrieved_at_utc"],
                "local_filename": rel, "file_hash_sha256": digest})
    row.update({k: str(v) for k, v in fields.items()})
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    new = not MANIFEST.exists()
    with MANIFEST.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow(row)


def months(first: str, last: str) -> list[str]:
    """Inclusive list of YYYYMM strings from 'YYYY-MM' to 'YYYY-MM'."""
    y, m = map(int, first.split("-"))
    y1, m1 = map(int, last.split("-"))
    out = []
    while (y, m) <= (y1, m1):
        out.append(f"{y:04d}{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out
