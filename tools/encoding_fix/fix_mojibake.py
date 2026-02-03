#!/usr/bin/env python3
"""Fix mojibake by attempting common encoding re-interpretations.

Workflow:
- Read file as UTF-8 (with replacement for invalid bytes).
- Try to recover by re-encoding to a legacy codec and decoding as UTF-8.
- Pick the candidate that reduces typical mojibake markers.
- Optionally write backups.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable, Tuple

# Heuristics: markers often seen in mojibake for Cyrillic
_BAD_MARKERS = [
    "Р", "р", "Ѓ", "ѓ", "Ћ", "љ", "ђ", "“", "”", "–", "—",
    "Ð", "Ñ", "Ã", "Â", "â€", "â€™", "â€œ", "â€�", "â€”",
    "", "", "�", "пїЅ",
]

_CANDIDATE_CODECS = [
    "cp1251",
    "koi8_r",
    "latin1",
]

_SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}

_SKIP_EXTS = {
    ".pyc",
    ".pyo",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".zip",
    ".7z",
    ".rar",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".mp3",
    ".mp4",
    ".mov",
    ".pdf",
    ".docx",
    ".xlsx",
    ".db",
    ".sqlite",
    ".bin",
    ".bak",
}

def _score(text: str) -> int:
    """Lower is better. Penalize mojibake markers and suspicious ratios."""
    score = 0
    for m in _BAD_MARKERS:
        score += text.count(m)

    # Penalize excessive ASCII control chars
    score += sum(1 for ch in text if ord(ch) < 9 or (13 < ord(ch) < 32))

    # Penalize overuse of 'Р' and 'С' which dominate cp1251<->utf8 mojibake
    cyr = [ch for ch in text if "\u0400" <= ch <= "\u04FF"]
    if cyr:
        rc = sum(1 for ch in cyr if ch in ("Р", "С"))
        ratio = rc / len(cyr)
        score += int(ratio * 100)

    # Prefer shorter text when other signals are equal (mojibake often expands)
    score += int(len(text) * 0.01)
    return score


def _try_fix(text: str, codec: str) -> str:
    """Attempt roundtrip: text -> codec bytes -> utf-8 text."""
    try:
        data = text.encode(codec, errors="replace")
        return data.decode("utf-8", errors="replace")
    except Exception:
        return text


def fix_text(text: str) -> Tuple[str, str]:
    """Return (best_text, codec_used)."""
    best = text
    best_codec = "original"
    best_score = _score(text)

    for codec in _CANDIDATE_CODECS:
        cand = _try_fix(text, codec)
        cand_score = _score(cand)
        if cand_score < best_score:
            best = cand
            best_codec = codec
            best_score = cand_score

    return best, best_codec


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == os.path.basename(__file__):
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in _SKIP_EXTS:
            continue
        yield path


def _looks_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:1024]
    except Exception:
        return True
    return b"\x00" in chunk


def process_file(path: Path, backup: bool) -> Tuple[bool, str]:
    if _looks_binary(path):
        return False, "binary_skip"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False, "read_error"

    # Only attempt fix if there are suspicious markers
    has_markers = any(m in text for m in _BAD_MARKERS)
    if not has_markers:
        return False, "unchanged"

    fixed, codec = fix_text(text)
    if fixed == text:
        return False, "unchanged"

    # Require a meaningful improvement
    if _score(fixed) >= _score(text) - 5:
        return False, "unchanged"

    if backup:
        backup_path = path.with_suffix(path.suffix + ".bak")
        if not backup_path.exists():
            backup_path.write_text(text, encoding="utf-8")

    try:
        path.write_text(fixed, encoding="utf-8")
    except Exception:
        return False, "write_error"

    return True, codec


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix mojibake by reinterpreting encodings.")
    parser.add_argument("root", nargs="?", default=".", help="Root folder to scan")
    parser.add_argument("--backup", action="store_true", help="Write .bak backups")
    parser.add_argument("--report", default="", help="Write report to file")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    changed = []
    unchanged = 0
    errors = 0

    for path in iter_files(root):
        ok, info = process_file(path, args.backup)
        if ok:
            changed.append((str(path), info))
        else:
            if info in ("read_error", "write_error"):
                errors += 1
            else:
                unchanged += 1

    lines = [
        f"root: {root}",
        f"changed: {len(changed)}",
        f"unchanged: {unchanged}",
        f"errors: {errors}",
        "",
    ]
    for p, codec in changed:
        lines.append(f"changed: {p} (codec: {codec})")

    report = "\n".join(lines)
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
