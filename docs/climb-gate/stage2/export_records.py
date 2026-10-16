# ruff: noqa: T201, D103, E501  # climb tooling: a CLI, prints are its output
"""Export the skill-trigger climb's per-run sidecar into evalharness records, one file per iteration.

Run with the kit's environment so the schema validator is importable:

    uv run --project ~/proj/evalharness python export_records.py \
        --runs runs.jsonl --eval-set ticket-eval.json --loop-json loop.json --out records/

A case is one query. A repeat is one `claude -p` run of that query under one description. The
criterion `trigger_matches_expectation` passes when a should-trigger query triggered or a
should-not query did not. The detector is recorded as the judge: model `trigger-detector`,
`prompt_sha256` the digest of the patched detector source. Cost is `unpriced`: the runs spend
subscription quota, not a priced API. The arm is the loop iteration whose description the run
used; a run whose description matches no iteration is refused, never guessed.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from evalharness.schema import load_schema, validate

HERE = Path(__file__).resolve().parent
SCHEMA = Path.home() / "proj/evalharness/docs/contract/record.schema.json"
DETECTOR = HERE / "patched/scripts/run_eval.py"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True, type=Path)
    ap.add_argument("--eval-set", required=True, type=Path)
    ap.add_argument("--loop-json", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    expect = {q["query"]: q["should_trigger"] for q in json.loads(args.eval_set.read_text())}
    case_id = {q: f"q{i:02d}" for i, q in enumerate(expect, 1)}
    loop = json.loads(args.loop_json.read_text())
    arm_of = {sha(h["description"]): f"iter{h['iteration']}" for h in loop["history"]}
    judge = {
        "model": "trigger-detector",
        "prompt_sha256": sha(DETECTOR.read_text()),
        "provider": None,
    }
    schema = load_schema(SCHEMA)

    runs = [json.loads(line) for line in args.runs.read_text().splitlines() if line.strip()]
    repeat: dict[tuple[str, str], int] = {}
    out_lines: dict[str, list[str]] = {}
    for r in runs:
        arm = arm_of.get(r["description_sha256"])
        if arm is None:
            sys.exit(
                f"run of {r['query'][:40]!r} used a description no iteration reports; refusing"
            )
        if r["query"] not in expect:
            sys.exit(f"run of an unknown query {r['query'][:40]!r}; refusing")
        k = (arm, r["query"])
        rep = repeat.get(k, 0)
        repeat[k] = rep + 1
        passed = r["triggered"] == expect[r["query"]]
        text = "triggered" if r["triggered"] else "not triggered"
        record = {
            "schema_version": "1",
            "case_id": case_id[r["query"]],
            "arm": arm,
            "repeat": rep,
            "response_text": text,
            "response_sha256": sha(text),
            "criteria": {
                "trigger_matches_expectation": {
                    "verdict": "pass" if passed else "fail",
                    "gating": True,
                    "reason": None,
                    "graded": None,
                }
            },
            "overall": "pass" if passed else "fail",
            "judge": judge,
            "cost": {
                "basis": "unpriced",
                "amount": None,
                "currency": None,
                "price_snapshot_date": None,
            },
            "latency": {"wall_ms": r["wall_ms"], "harness_ms": r["harness_ms"]},
            "failure_class": "none",
            "provenance": {
                "served_model": r.get("served_model"),
                "provider": "claude-code",
                "sampling": None,
                "weights_digest": None,
            },
            "started_at": r["started_at"],
        }
        errors = validate(json.loads(json.dumps(record)), schema)
        if errors:
            sys.exit(f"record fails the contract: {errors}")
        out_lines.setdefault(arm, []).append(json.dumps(record))
    args.out.mkdir(parents=True, exist_ok=True)
    for arm, lines in sorted(out_lines.items()):
        (args.out / f"{arm}.jsonl").write_text("\n".join(lines) + "\n")
        print(f"{arm}: {len(lines)} records", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
