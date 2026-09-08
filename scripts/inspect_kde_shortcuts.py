#!/usr/bin/env python3
"""Print MagicScribe/F8/F9 entries from KDE's global-shortcut config.

Diagnostic only: this script never writes KDE configuration.
"""

from __future__ import annotations

import os
from pathlib import Path


def main() -> int:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = config_home / "kglobalshortcutsrc"
    print(f"KDE global-shortcut config: {path}")
    if not path.is_file():
        print("File non trovato.")
        return 1

    section = ""
    matches: list[tuple[int, str, str]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped
            if "magicscribe" in stripped.lower():
                matches.append((line_no, section, stripped))
            continue

        haystack = f"{section} {stripped}".lower()
        if (
            "magicscribe" in haystack
            or "f8" in stripped.lower()
            or "f9" in stripped.lower()
        ):
            matches.append((line_no, section, stripped))

    if not matches:
        print("Nessuna voce MagicScribe/F8/F9 trovata.")
        return 0

    current = None
    for line_no, matched_section, text in matches:
        if matched_section != current:
            current = matched_section
            if current:
                print(f"\n{current}")
        print(f"{line_no}: {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
