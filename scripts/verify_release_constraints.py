#!/usr/bin/env python3
"""Verifica che ogni dipendenza diretta abbia un pin release esplicito.

I file requirements*.txt descrivono il contratto di compatibilita'. I file
constraints*.txt selezionano invece le versioni esatte usate dall'installer e
dalla CI. Questo check impedisce di aggiungere una nuova dipendenza diretta
senza aggiornare anche il set riproducibile.
"""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
_NAME_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")
_EXACT_PIN_RE = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)(?:\s*;.*)?$"
)


def _normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _logical_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def _direct_requirement_names(path: Path) -> set[str]:
    names: set[str] = set()
    for line in _logical_lines(path):
        if line.startswith(("-r ", "--requirement ", "-c ", "--constraint ")):
            continue
        match = _NAME_RE.match(line)
        if match is None:
            raise SystemExit(f"Requirement non riconosciuto in {path.name}: {line}")
        names.add(_normalized_name(match.group(1)))
    return names


def _constraint_pins(path: Path, seen: set[Path] | None = None) -> dict[str, str]:
    resolved = path.resolve()
    visited = set() if seen is None else seen
    if resolved in visited:
        return {}
    visited.add(resolved)

    pins: dict[str, str] = {}
    for line in _logical_lines(path):
        if line.startswith(("-c ", "--constraint ")):
            include = line.split(maxsplit=1)[1]
            pins.update(_constraint_pins(path.parent / include, visited))
            continue
        if line.startswith(("-r ", "--requirement ")):
            raise SystemExit(
                f"{path.name}: usare solo constraints inclusi, non requirements: {line}"
            )

        match = _EXACT_PIN_RE.match(line)
        if match is None:
            raise SystemExit(
                f"Constraint non esatto in {path.name}: {line}; richiesto package==version"
            )
        name = _normalized_name(match.group(1))
        version = match.group(2)
        previous = pins.get(name)
        if previous is not None and previous != version:
            raise SystemExit(
                f"Pin conflittuale per {name}: {previous} vs {version}"
            )
        pins[name] = version
    return pins


def _assert_exact_coverage(label: str, required: set[str], pins: dict[str, str]) -> None:
    pinned = set(pins)
    missing = sorted(required - pinned)
    stale = sorted(pinned - required)
    if missing or stale:
        details = []
        if missing:
            details.append("mancano pin: " + ", ".join(missing))
        if stale:
            details.append("pin senza requirement: " + ", ".join(stale))
        raise SystemExit(f"{label}: " + "; ".join(details))


def main() -> None:
    runtime = _direct_requirement_names(ROOT / "requirements.txt")
    dev = _direct_requirement_names(ROOT / "requirements-dev.txt")
    release_pins = _constraint_pins(ROOT / "constraints-release.txt")
    ci_pins = _constraint_pins(ROOT / "constraints-ci.txt")

    _assert_exact_coverage("release", runtime, release_pins)
    _assert_exact_coverage("ci", runtime | dev, ci_pins)

    release_summary = ", ".join(
        f"{name}=={release_pins[name]}" for name in sorted(release_pins)
    )
    ci_only = sorted((runtime | dev) - runtime)
    ci_summary = ", ".join(f"{name}=={ci_pins[name]}" for name in ci_only)
    print(f"Release constraints OK: {release_summary}")
    if ci_summary:
        print(f"CI-only constraints OK: {ci_summary}")


if __name__ == "__main__":
    main()
