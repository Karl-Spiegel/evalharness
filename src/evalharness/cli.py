"""Command-line entry point. Parses arguments, builds dependencies, calls the library."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import IO

from evalharness.schema import RECORD_SCHEMA, load_schema
from evalharness.verdict import RecordFileError, load_records, render


def run(argv: Sequence[str], stdout: IO[str], stderr: IO[str]) -> int:
    """Run the CLI against explicit streams; return the exit status. Tests call this."""
    parser = argparse.ArgumentParser(prog="evalharness")
    parser.description = "A record-first harness for LLM evals."
    commands = parser.add_subparsers(dest="command", required=True)
    verdict = commands.add_parser("verdict", help="compare two arms' record files in one line")
    verdict.add_argument("--a", type=Path, required=True, help="record JSONL file of arm A")
    verdict.add_argument("--b", type=Path, required=True, help="record JSONL file of arm B")
    verdict.add_argument("--label-a", default="A", help="label of arm A in the line")
    verdict.add_argument("--label-b", default="B", help="label of arm B in the line")
    args = parser.parse_args(argv)
    schema = load_schema(RECORD_SCHEMA)
    try:
        a = load_records(args.a, schema)
        b = load_records(args.b, schema)
    except RecordFileError as e:
        stderr.write(f"error: {e}\n")
        return 2
    stdout.write(render(a, b, args.label_a, args.label_b) + "\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Console-script entry: real streams, real argv."""
    return run(sys.argv[1:] if argv is None else argv, sys.stdout, sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
