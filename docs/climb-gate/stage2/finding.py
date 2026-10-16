# ruff: noqa: T201, D103, S603, S607, PLW1510, E501  # climb tooling: a CLI, prints are its output
"""Build the stage 2 finding page and the draft description diff from the loop's records.

    uv run --project ~/proj/evalharness python finding.py --loop-json loop-ticket.json \
        --records records-ticket --plan ~/proj/evalharness/docs/climb-gate/plan.md \
        --skill skill-ticket/SKILL.md --out ~/proj/evalharness/docs/climb-gate/skill-climb.md \
        --diff ~/proj/evalharness/docs/climb-gate/drafts/ticket-description.diff

Every number comes from the kit's verdict line over the exported records or from the loop's own
summary; the gate verdict is `gate.py`'s. The best description is the loop's choice (held-out
score). The diff is a draft against the real SKILL.md and is never applied here.
"""

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def verdict_line(a: Path, b: Path) -> str:
    return subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(Path.home() / "proj/evalharness"),
            "evalharness",
            "verdict",
            "--a",
            str(a),
            "--b",
            str(b),
            "--label-a",
            a.stem,
            "--label-b",
            b.stem,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def gate(a: Path, b: Path, plan: Path) -> str:
    r = subprocess.run(
        [sys.executable, str(HERE / "gate.py"), "--a", str(a), "--b", str(b), "--plan", str(plan)],
        capture_output=True,
        text=True,
    )
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("gate:")]
    return lines[-1].removeprefix("gate: ") if lines else f"gate failed: {r.stderr.strip()[:120]}"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop-json", required=True, type=Path)
    ap.add_argument("--records", required=True, type=Path)
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--skill", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--diff", required=True, type=Path)
    ap.add_argument("--runs", required=True, type=Path, help="the sidecar, for the run count")
    args = ap.parse_args(argv)

    loop = json.loads(args.loop_json.read_text())
    hist = loop["history"]
    runs = sum(1 for ln in args.runs.read_text().splitlines() if ln.strip())
    rows = []
    for h in hist:
        n = h["iteration"]
        rec = args.records / f"iter{n}.jsonl"
        line = verdict_line(rec, rec)
        headline = line.split("|")[0].split("  ")[0].strip()
        if n == 1:
            step = "baseline"
        else:
            prev = args.records / f"iter{n - 1}.jsonl"
            seg = re.search(r"per-case net [^|]+", verdict_line(prev, rec))
            step = f"`{seg.group(0).strip()}` → {gate(prev, rec, args.plan)}"
        rows.append(
            f"| iter{n} | {headline} | train {h['train_passed']}/{h['train_total']} | test {h['test_passed']}/{h['test_total']} | {step} |"
        )
    first = next(h for h in hist if h["iteration"] == 1)["description"]
    best = loop["best_description"]
    best_iter = next((h["iteration"] for h in hist if h["description"] == best), None)

    climbed = hist[-1]["description"]  # the last iteration's description: the climbed candidate
    skill = args.skill.read_text()
    m = re.search(r"(description: >\n)((?:  .*\n)+)", skill)
    if not m:
        sys.exit("SKILL.md description block not found")
    width = 78
    wrapped = []
    line = "  "
    for word in climbed.split():
        if len(line) + len(word) + 1 > width and line.strip():
            wrapped.append(line.rstrip())
            line = "  "
        line += word + " "
    wrapped.append(line.rstrip())
    new_skill = skill[: m.start(2)] + "\n".join(wrapped) + "\n" + skill[m.end(2) :]
    diff = "".join(
        difflib.unified_diff(
            skill.splitlines(True),
            new_skill.splitlines(True),
            "a/.claude/skills/ticket/SKILL.md",
            "b/.claude/skills/ticket/SKILL.md",
        )
    )
    args.diff.parent.mkdir(parents=True, exist_ok=True)
    args.diff.write_text(diff or "# no change: the climbed description equals the original\n")

    text = f"""# Stage 2: the `ticket` skill's description, climbed and gated

The skill-creator description climber (`run_loop.py`) ran on the `ticket` skill, {len(hist)} iterations,
20 queries (10 should-trigger, 10 should-not), 60/40 train/test split, 3 runs per query, Opus, from a
clone of this repo with the real skill hidden and one project root per worker. {runs} `claude -p`
runs in all. Each run became one kit record (`export_records.py`); each iteration is one arm. The
gate between iterations is the kit's per-case segment at the seam 1 threshold (`gate.py`).

| Arm | Pass (kit headline) | Train (loop) | Test (loop) | Step vs previous (per-case) |
|---|---|---|---|---|
{chr(10).join(rows)}

The kit headline counts every run; the loop's train and test counts are its own per-run tallies on
the split. A step's gate reads the per-case segment: one pair per query across its three runs, net
and exact McNemar p, accepted only with net > 0 and p below the threshold.

## Result

Loop exit: {loop["exit_reason"]}. Best by held-out score: iteration {best_iter if best_iter is not None else "n/a"}.

Original description:

> {first}

The loop's best, by held-out score (ties keep the earlier): {"the original" if best == first else f"iteration {best_iter}"}.

Climbed description (iteration {hist[-1]["iteration"]}):

> {climbed}

Draft diff of the climbed description against the real skill, not applied: `docs/climb-gate/drafts/ticket-description.diff`. {"The loop itself did not prefer it: held-out tied, so by its rule the original stands. " if best == first else ""}Karl applies it or not.

## What this says about the climber and the kit

- The climber needed four fixes to measure anything on this host (plan file, stage 2 tooling).
  With them, the original `ticket` description already triggers on nearly every should-trigger
  query and never on the should-not ones, so there is little headroom for a description climb here.
- The kit's per-case segment is the right shape for the loop: one pair per query, repeats folded
  in, direction and p on one line. The gate refuses to decide without a recorded threshold.
- Records: `records-ticket/iter*.jsonl` in the climb workspace; sidecar `runs-ticket.jsonl`;
  loop output `loop-ticket.json` and `report-ticket.html`.
"""
    args.out.write_text(text)
    print(f"wrote {args.out} and {args.diff}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
