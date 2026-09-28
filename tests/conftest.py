"""Suite-wide invariants. Full spec: ~/.claude/skills/test-invariants/.

T1: production-scale tests are pinned by node id in FULL_SCALE_TESTS (drift test in
    test_invariants.py).
T2: hermetic. $HOME and every XDG path live in the per-test tmp dir; the environment is a
    closed allowlist; cloud and password-manager CLIs are poisoned on PATH; pytest-socket
    (addopts in pyproject.toml) blocks the network.
T4: no per-test executables: the poison stubs are one script plus symlinks, made once per session.
"""

import os
import stat
from collections.abc import Iterator
from pathlib import Path

import pytest

# Node ids of tests that may run at production scale. Add a row deliberately, with a
# justification in the diff. The drift test fails when this set and the marked tests differ.
FULL_SCALE_TESTS: frozenset[str] = frozenset()

# Environment variables a test process may inherit. Everything else is removed. Denylists rot;
# allowlists fail closed.
ENV_ALLOW_EXACT = frozenset(
    {
        "PATH",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TERM",
        "TZ",
        "TMPDIR",
        "CI",
        "VIRTUAL_ENV",
        "PWD",
        "SHELL",
        "USER",
        "LOGNAME",
    }
)
ENV_ALLOW_PREFIX = ("PYTEST_", "PYTHON", "COV_CORE_", "COVERAGE_", "UV_", "HYPOTHESIS_")

# Binaries a test must never reach. One stub script, one symlink per name (T4).
POISONED_BINARIES = ("gh", "aws", "gcloud", "az", "op", "kubectl", "docker", "ssh", "curl", "wget")

MARKED_FULL_SCALE: set[str] = set()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Record every test that carries the full_scale marker (consumed by the drift test)."""
    for item in items:
        if item.get_closest_marker("full_scale") is not None:
            MARKED_FULL_SCALE.add(item.nodeid)


@pytest.fixture(scope="session", autouse=True)
def _poison_binaries(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Put failing stubs of external CLIs first on PATH for the whole session."""
    bin_dir = tmp_path_factory.mktemp("poison")
    stub = bin_dir / "_poison"
    stub.write_text(
        '#!/bin/sh\necho "test invariant T2: $(basename "$0") is poisoned in tests" >&2\nexit 97\n'
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    for name in POISONED_BINARIES:
        (bin_dir / name).symlink_to(stub)
    original = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{original}"
    try:
        yield
    finally:
        os.environ["PATH"] = original


@pytest.fixture(autouse=True)
def _hermetic_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Closed-allowlist environment with every user path rooted in the per-test tmp dir."""
    for key in list(os.environ):
        if key in ENV_ALLOW_EXACT or key.startswith(ENV_ALLOW_PREFIX):
            continue
        monkeypatch.delenv(key, raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / ".local" / "state"))
