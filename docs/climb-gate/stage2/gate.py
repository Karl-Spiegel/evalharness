# ruff: noqa: T201, D103, S603, S607, E501  # climb tooling: a CLI, prints are its output
"""Gate one climb iteration against the previous one with the kit's per-case segment.

    uv run --project ~/proj/evalharness python gate.py --a records/iter1.jsonl --b records/iter2.jsonl \
        --plan ~/proj/evalharness/docs/climb-gate/plan.md

The threshold is read from the plan file's "Seam 1 answers" section, as a line
`threshold: p < 0.05` written by Karl. No ruling there means the gate cannot run: it prints
`threshold unrecorded` and exits 3. It never falls back to a default. Acceptance: the per-case
net is above zero and the two-sided p is below the threshold. A significant loss is a
rejection; anything else is `no decision`.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

SEGMENT = re.compile(
    r"per-case net (\S+) \((\S+)>(\S+) (\S+), (\S+)>(\S+) (\S+), cases (\d+), p (\S+)\)"
)


def threshold_from_plan(plan: Path) -> float | None:
    text = plan.read_text()
    m = re.search(r"### Seam 1 answers\n(.*?)(?:\n### |\Z)", text, re.DOTALL)
    if not m:
        return None
    t = re.search(r"threshold:\s*p\s*<\s*([0-9.]+)", m.group(1))
    return float(t.group(1)) if t else None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, type=Path)
    ap.add_argument("--b", required=True, type=Path)
    ap.add_argument("--plan", required=True, type=Path)
    args = ap.parse_args(argv)
    threshold = threshold_from_plan(args.plan)
    line = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(Path.home() / "proj/evalharness"),
            "evalharness",
            "verdict",
            "--a",
            str(args.a),
            "--b",
            str(args.b),
            "--label-a",
            args.a.stem,
            "--label-b",
            args.b.stem,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    print(line)
    m = SEGMENT.search(line)
    if not m:
        sys.exit("no per-case segment in the verdict line")
    net, p = m.group(1), m.group(9)
    if threshold is None:
        print("gate: threshold unrecorded (no ruling under 'Seam 1 answers'); cannot decide")
        return 3
    if net == "n/a" or p == "n/a":
        print(f"gate: no decision (net {net}, p {p})")
        return 1
    net_v, p_v = int(net), float(p)
    if p_v < threshold and net_v > 0:
        print(
            f"gate: ACCEPT {args.b.stem} over {args.a.stem} (net {net_v:+d}, p {p_v} < {threshold})"
        )
        return 0
    if p_v < threshold and net_v < 0:
        print(
            f"gate: REJECT {args.b.stem}, significant loss (net {net_v:+d}, p {p_v} < {threshold})"
        )
        return 2
    print(f"gate: no decision (net {net_v:+d}, p {p_v} >= {threshold})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
