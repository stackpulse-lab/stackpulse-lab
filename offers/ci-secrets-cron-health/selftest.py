#!/usr/bin/env python3
"""Self-test for the offer package: stdlib only, no network.

Checks that every required file exists, both JSON manifests parse, the intake
form is free of obvious secret material, and Markdown relative links resolve.
Run from the offer directory:

    python3 selftest.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED = [
    "README.md",
    "selftest.py",
    "templates/intake.yml",
    "templates/audit-checklist.md",
    "templates/delivery-report.md",
    "templates/cron-manifest.example.json",
    "templates/timers.example.json",
]

# Deliberately crude: catches pasted tokens, not every possible secret.
SUSPICIOUS = [
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"https://open\.feishu\.cn/open-apis/bot/v2/hook/[0-9a-f-]{20,}"),
]

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def check_files(errors: list[str]) -> None:
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            errors.append(f"missing file: {rel}")


def check_json(errors: list[str], notes: list[str]) -> None:
    for rel, key in (
        ("templates/cron-manifest.example.json", "entries"),
        ("templates/timers.example.json", "timers"),
    ):
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{rel}: invalid JSON: {exc}")
            continue
        items = payload.get(key) if isinstance(payload, dict) else None
        if not isinstance(items, list) or not items:
            errors.append(f"{rel}: expected a non-empty '{key}' list")
            continue
        notes.append(f"{rel}: {len(items)} {key}")


def check_yaml(errors: list[str], notes: list[str]) -> None:
    path = ROOT / "templates/intake.yml"
    if not path.is_file():
        return
    try:
        import yaml  # type: ignore
    except ImportError:
        notes.append("intake.yml: PyYAML not installed, syntax check skipped")
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(f"intake.yml: invalid YAML: {exc}")
        return
    if not isinstance(data, dict) or data.get("declaration", {}).get("no_secrets_included") is not True:
        errors.append("intake.yml: declaration.no_secrets_included must be true")
        return
    notes.append("intake.yml: parsed, declaration.no_secrets_included=true")


def check_secrets(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix in {".pyc"} or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in SUSPICIOUS:
            match = pattern.search(text)
            if match:
                errors.append(f"{path.relative_to(ROOT)}: looks like a real credential ({pattern.pattern[:24]}…)")


def check_links(errors: list[str], notes: list[str]) -> None:
    checked = 0
    for path in sorted(ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for target in LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean = target.split("#", 1)[0]
            if not clean:
                continue
            if not (path.parent / clean).exists():
                errors.append(f"{path.relative_to(ROOT)}: broken link -> {target}")
            checked += 1
    notes.append(f"markdown links checked: {checked}")


def main() -> int:
    errors: list[str] = []
    notes: list[str] = []
    check_files(errors)
    check_json(errors, notes)
    check_yaml(errors, notes)
    check_secrets(errors)
    check_links(errors, notes)

    for note in notes:
        print(f"ok   {note}")
    for error in errors:
        print(f"FAIL {error}")
    if errors:
        print(f"\n{len(errors)} problem(s)")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
