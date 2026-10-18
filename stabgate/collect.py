"""Download JUnit XML artifacts of recent GitHub Actions runs (via the `gh` CLI) into a directory, with run metadata,
so the directory can be fed to flakemap. File names carry sha/branch: <run_id>__<sha7>__<branch>__<artifact>.xml"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout


def safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s)


def run_meta(repo: str, limit: int) -> list[dict]:
    out = _gh("run", "list", "-R", repo, "--limit", str(limit), "--json", "databaseId,headSha,headBranch,conclusion")
    return json.loads(out)


def collect(repo: str, dest: Path, artifact_prefix: str = "junit", limit: int = 30) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for run in run_meta(repo, limit):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                _gh("run", "download", str(run["databaseId"]), "-R", repo, "-p", f"{artifact_prefix}*", "-D", tmp)
            except subprocess.CalledProcessError:
                continue  # run has no such artifact (or expired)
            for xml in Path(tmp).rglob("*.xml"):
                name = f"{run['databaseId']}__{run['headSha'][:7]}__{safe(run['headBranch'])}__{safe(xml.parent.name)}.xml"
                target = dest / name
                target.write_bytes(xml.read_bytes())
                written.append(target)
    return written
