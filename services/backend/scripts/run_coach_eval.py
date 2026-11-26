"""Run the coach evaluation suite.

    python scripts/run_coach_eval.py                      # stand-in provider, free, used in CI
    python scripts/run_coach_eval.py --provider anthropic --confirm-cost --out report.json

The live run calls the configured model once per case (about 30 calls) and is billed to the account
behind PDNA_ANTHROPIC_API_KEY. It refuses to run without --confirm-cost.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.coaching import evaluation
from app.coaching.prompts import load_prompt
from app.coaching.providers import MockProvider, make_provider
from app.core.config import Settings


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--provider", choices=["mock", "anthropic"], default="mock")
    parser.add_argument("--confirm-cost", action="store_true", help="required for paid providers")
    parser.add_argument("--suite", action="append", help="run only these suites (repeatable)")
    parser.add_argument("--prompt", default="coach.v1.md")
    parser.add_argument("--out", type=Path, help="write the full JSON report here")
    args = parser.parse_args()

    if args.provider == "mock":
        provider = MockProvider()
    else:
        if not args.confirm_cost:
            parser.error("a live run is billed per call; pass --confirm-cost to proceed")
        provider = make_provider(Settings(coach_provider="anthropic"))
    report = evaluation.run(provider, load_prompt(args.prompt), only=set(args.suite or []))

    for suite, r in report.rates().items():
        print(f"{suite:14} {int(r['cases']):3d} cases   model {r['model']:7.2%}   system {r['system']:7.2%}")
    for c in report.cases:
        if not c.model_pass:
            print(f"  FAIL {c.id}: {'; '.join(c.problems)}")
    if args.out:
        args.out.write_text(json.dumps(report.to_json(), indent=2), encoding="utf-8")
    failures = report.failures()
    for f in failures:
        print(f"THRESHOLD {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
