from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import params, runner, select, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="stabgate", description="Repeat new/changed pytest tests N times; fail on mixed results.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("check", help="run the gate on the diff against --base")
    g.add_argument("--base", default="origin/main")
    g.add_argument("--repo", default=".")
    g.add_argument("-n", "--runs", type=int, default=20)
    g.add_argument("--max-params", type=int, default=3, help="max parametrizations per test function")
    g.add_argument("--out", default=".stabgate", help="dir for per-run JUnit XML (feed it to flakemap)")
    g.add_argument("--python", default=sys.executable)
    g.add_argument("--json", action="store_true")

    c = sub.add_parser("calibrate", help="how many runs to catch a flaky test of failure prob p?")
    c.add_argument("--p", type=float, required=True)
    c.add_argument("--target", type=float, default=0.9)

    a = ap.parse_args(argv)
    if a.cmd == "calibrate":
        n = stats.min_runs(a.p, a.target)
        print(f"p={a.p}: need N={n} runs for >={a.target:.0%} detection "
              f"(analytic {stats.detect_prob(a.p, n):.1%}, simulated {stats.simulate(a.p, n):.1%}); N=10 gives {stats.detect_prob(a.p, 10):.1%}")
        return 0

    repo = Path(a.repo).resolve()
    changed = select.changed_files(a.base, repo)
    chosen = select.affected_tests(changed, repo)
    if not chosen:
        print("stabgate: no new/changed tests (and no tests importing changed modules).")
        return 0
    ids = params.sample(params.collect(sorted(chosen), repo, a.python), a.max_params)
    files = runner.run_n(ids, a.runs, repo, repo / a.out, a.python)
    v = runner.verdicts(files)
    bad = {t: r for t, r in v.items() if r["verdict"] in ("flaky", "broken")}
    if a.json:
        print(json.dumps({"selected": chosen, "runs": len(files), "verdicts": v}, indent=1))
    else:
        print(f"stabgate: {len(ids)} test(s) from {len(chosen)} file(s) x {len(files)} runs")
        for f, why in sorted(chosen.items()):
            print(f"  {f}  ({why})")
        for t, r in sorted(bad.items()):
            print(f"  {r['verdict'].upper()}: {t}  pass={r['pass']} fail={r['fail']}")
        if not bad:
            print("  all stable")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
