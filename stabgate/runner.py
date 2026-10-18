from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def junit_results(path: Path) -> dict[str, str]:
    """{test id: 'pass'|'fail'|'skip'} from a JUnit XML file."""
    res: dict[str, str] = {}
    for tc in ET.parse(path).getroot().iter("testcase"):
        tid = f"{tc.get('classname', '')}::{tc.get('name', '')}"
        if tc.find("failure") is not None or tc.find("error") is not None:
            res[tid] = "fail"
        elif tc.find("skipped") is not None:
            res[tid] = "skip"
        else:
            res[tid] = "pass"
    return res


def run_n(nodeids: list[str], n: int, repo: Path, out_dir: Path, python: str = "python") -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for i in range(1, n + 1):
        xml = out_dir / f"run-{i:03d}.xml"
        subprocess.run(
            [python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:randomly", f"--junitxml={xml}", *nodeids],
            cwd=repo, capture_output=True, stdin=subprocess.DEVNULL,
        )
        if xml.exists():
            files.append(xml)
    return files


def verdicts(files: list[Path]) -> dict[str, dict]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"pass": 0, "fail": 0, "skip": 0})
    for f in files:
        for tid, st in junit_results(f).items():
            counts[tid][st] += 1
    out = {}
    for tid, c in counts.items():
        if c["pass"] and c["fail"]:
            v = "flaky"
        elif c["fail"] and not c["pass"]:
            v = "broken"
        else:
            v = "stable"
        out[tid] = {**c, "verdict": v}
    return out
