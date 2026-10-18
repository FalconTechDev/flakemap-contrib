from __future__ import annotations

import re
import subprocess
from pathlib import Path


def collect(files: list[str], repo: Path, python: str = "python") -> list[str]:
    out = subprocess.run(
        [python, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", *files],
        cwd=repo, capture_output=True, text=True, stdin=subprocess.DEVNULL,
    ).stdout
    return [l.strip() for l in out.splitlines() if "::" in l and not l.startswith(" ")]


def sample(nodeids: list[str], max_params: int) -> list[str]:
    """Keep at most `max_params` parametrizations per test function, evenly spaced (deterministic)."""
    groups: dict[str, list[str]] = {}
    for n in nodeids:
        groups.setdefault(re.sub(r"\[.*\]$", "", n), []).append(n)
    keep: list[str] = []
    for ids in groups.values():
        if len(ids) <= max_params:
            keep += ids
        else:
            step = (len(ids) - 1) / (max_params - 1) if max_params > 1 else 0
            keep += [ids[round(i * step)] for i in range(max_params)]
    return keep
