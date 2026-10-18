# stabgate — a stability gate for pytest (companion to flakemap)

On a PR, rerun the **new and changed tests** — plus tests that import a changed module — N times and **fail on mixed
results** (same test passed and failed). Idea from the 2GIS write-up (habr.com/ru/companies/2gis/articles/1074116): their
gate misses changes in helpers, runs every parametrization, and needs hand-written regexes for known flakes. This tool addresses the first two:

* **Selection:** `git diff base...HEAD` → changed `test_*.py` / `*_test.py`, plus tests whose imports (transitively, local `.py` files, AST-based) reach a changed module.
* **Parametrization:** at most `--max-params` (default 3) evenly-spaced cases per test function.
* **Verdicts:** `flaky` (mixed), `broken` (always fails), `stable`. Exit 1 on flaky/broken.
* **flakemap-friendly:** every run writes JUnit XML to `.stabgate/run-NNN.xml`; `stabgate.collect` pulls JUnit artifacts from past Actions runs (via `gh`) into one directory named `<run>__<sha>__<branch>__<artifact>.xml`.

```
pip install -e .
stabgate check --base origin/main -n 22
stabgate calibrate --p 0.1 --target 0.9
```

## Choosing N (this corrects the brief)
A test failing independently with probability p shows mixed results in N runs with probability ≈ 1−(1−p)^N.
* The brief's target "catch p ≥ 10% at N=10 in ≥ 90% of runs" is **mathematically unreachable**: N=10 gives **65.1%**. Reaching 90% needs **N=22** (`stabgate calibrate --p 0.1`; confirmed by simulation in the tests).
* False positives on genuinely deterministic stable tests are 0 by construction (no failures ⇒ never "mixed"). A test that is flaky at p=0.01 will be missed ~80% of the time at N=22 — the gate catches *egregious* flakes, it does not certify stability.

## Limits (honest)
* Python/pytest only. Import graph is static (`import x`, `from x import y`); dynamic imports, `conftest.py` fixtures, data files and `src/` layouts are not followed.
* Independent-failure model; flakes that depend on test order/parallelism/time of day are not modelled. Tests run sequentially in one process per run; `-p no:randomly` is passed.
* Stage 0 of the brief (reading flakemap issues, deflaky-cli, Mergify, labelled datasets, contacting the flakemap author) was **not done**: no draft issue was sent anywhere. flakemap 0.3.7 exists on PyPI (verified by download); nothing else about it was re-checked. Calibration against a labelled corpus: not done (none located).
* The collector is tested against a mocked `gh`, not a live repository.

## Dev
`pip install -e .[dev] && pytest` (needs git).
