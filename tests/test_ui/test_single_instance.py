"""Tests for the Linux single-instance runtime guard."""

from __future__ import annotations

from ui.native.single_instance import SingleInstanceGuard


def test_single_instance_guard_is_exclusive_and_reusable(tmp_path) -> None:
    lock_path = tmp_path / "runtime.lock"
    first = SingleInstanceGuard(lock_path)
    second = SingleInstanceGuard(lock_path)

    assert first.acquire() is True
    assert first.acquire() is True
    assert second.acquire() is False

    first.release()
    assert second.acquire() is True
    second.release()


def test_single_instance_guard_writes_owner_pid(tmp_path) -> None:
    lock_path = tmp_path / "runtime.lock"
    guard = SingleInstanceGuard(lock_path)

    assert guard.acquire() is True
    owner = lock_path.read_text(encoding="ascii").strip()
    assert owner.isdigit()

    guard.release()
