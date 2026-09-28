"""Command-line entry point. Parses arguments, builds dependencies, calls the library."""

import argparse
import sys
from collections.abc import Sequence
from typing import IO

from evalharness import greeting


def run(argv: Sequence[str], stdout: IO[str], stderr: IO[str]) -> int:
    """Run the CLI against explicit streams; return the exit status. Tests call this."""
    parser = argparse.ArgumentParser(prog="evalharness")
    parser.description = "A record-first harness for LLM evals."
    parser.add_argument("name", help="who to greet")
    args = parser.parse_args(argv)
    try:
        stdout.write(greeting(args.name) + "\n")
    except ValueError as e:
        stderr.write(f"error: {e}\n")
        return 2
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Console-script entry: real streams, real argv."""
    return run(sys.argv[1:] if argv is None else argv, sys.stdout, sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
