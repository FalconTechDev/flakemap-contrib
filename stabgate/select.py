"""Pick the tests a change could affect: changed test files + test files that import (transitively) a changed module."""
from __future__ import annotations

import ast
import subprocess
from pathlib import Path


def changed_files(base: str, repo: Path) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AMR", f"{base}...HEAD"],
        cwd=repo, capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL,
    ).stdout
    return [l.strip() for l in out.splitlines() if l.strip().endswith(".py")]


def is_test_file(rel: str) -> bool:
    name = Path(rel).name
    return name.startswith("test_") or name.endswith("_test.py")


def _module_name(rel: str) -> str:
    parts = list(Path(rel).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def imports_of(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
            names |= {f"{node.module}.{a.name}" for a in node.names}
    return names


def affected_tests(changed: list[str], repo: Path) -> dict[str, str]:
    """Return {test file: reason}. Reasons: 'changed' or 'imports <module>' (transitive via local modules)."""
    py = [str(p.relative_to(repo)).replace("\\", "/") for p in repo.rglob("*.py")
          if not any(part.startswith(".") or part in {"node_modules", "venv", "__pycache__", "site-packages"} for part in p.relative_to(repo).parts)]
    modname = {rel: _module_name(rel) for rel in py}
    graph = {rel: imports_of(repo / rel) for rel in py}

    result: dict[str, str] = {c: "changed" for c in changed if is_test_file(c)}
    dirty = {modname[c] for c in changed if c in modname and not is_test_file(c)}
    seen = set(dirty)
    frontier = set(dirty)
    while frontier:
        nxt = set()
        for rel, imps in graph.items():
            if rel in result or is_test_file(rel):
                continue
            hit = next((m for m in frontier if any(i == m or i.startswith(m + ".") for i in imps)), None)
            if hit and modname[rel] not in seen:
                seen.add(modname[rel])
                nxt.add(modname[rel])
        frontier = nxt
        dirty |= nxt
    for rel in py:
        if not is_test_file(rel) or rel in result:
            continue
        hit = next((m for m in sorted(dirty) if any(i == m or i.startswith(m + ".") for i in graph[rel])), None)
        if hit:
            result[rel] = f"imports {hit}"
    return result
