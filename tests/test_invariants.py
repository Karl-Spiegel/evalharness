"""Guards for the test-suite invariants. Each guard fails loud when it has nothing to check (T5)."""

import re
import socket
from pathlib import Path

import pytest
from pytest_socket import SocketBlockedError

from tests.conftest import FULL_SCALE_TESTS, MARKED_FULL_SCALE

TESTS_DIR = Path(__file__).parent
HOME_RESOLUTION = re.compile(
    r"expanduser\(|Path\.home\(|os\.environ\[.HOME.\]|environ\.get\(.HOME|\$HOME"
)
SELF = {"conftest.py", Path(__file__).name}


def test_full_scale_tests_are_pinned() -> None:
    """T1: the tests marked full_scale are exactly the pinned set, by node id."""
    assert set(FULL_SCALE_TESTS) == MARKED_FULL_SCALE, (
        "full_scale drift. Marked but not pinned: "
        f"{sorted(MARKED_FULL_SCALE - FULL_SCALE_TESTS)}; pinned but not marked: "
        f"{sorted(FULL_SCALE_TESTS - MARKED_FULL_SCALE)}. Update FULL_SCALE_TESTS in "
        "tests/conftest.py deliberately and justify the change in the diff."
    )


def test_no_test_resolves_home() -> None:
    """T2: no test file reads $HOME or expands a user path (conftest.py is the one that sets it)."""
    files = [p for p in TESTS_DIR.rglob("*.py") if p.name not in SELF]
    if not files:
        pytest.fail("guard collected zero test files; the guard is dead, not passing")
    offenders = [
        f"{p.relative_to(TESTS_DIR)}:{n}"
        for p in files
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if HOME_RESOLUTION.search(line)
    ]
    assert not offenders, f"tests must root every path under tmp_path, not $HOME: {offenders}"


def test_network_is_blocked() -> None:
    """T2: pytest-socket is active (addopts in pyproject.toml), so opening a socket raises."""
    with pytest.warns(UserWarning, match="socket"), pytest.raises(SocketBlockedError):
        socket.socket()
