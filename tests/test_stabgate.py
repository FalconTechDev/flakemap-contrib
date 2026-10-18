import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from stabgate import cli, params, select, stats


def test_min_runs_matches_math():
    assert stats.min_runs(0.1, 0.9) == 22
    assert stats.detect_prob(0.1, 10) == pytest.approx(0.6513, abs=1e-4)  # N=10 can NOT reach 90% for p=10%


def test_simulation_agrees_with_analytic():
    # mixed results needs at least one pass AND one fail; for p=0.1,N=22 that is ~ 1-(0.9^22)-(0.1^22)
    assert stats.simulate(0.1, 22, trials=20000) == pytest.approx(stats.detect_prob(0.1, 22), abs=0.015)


def test_stable_test_never_flagged():
    assert stats.simulate(0.0, 50, trials=2000) == 0.0


def test_param_sampling_is_bounded_and_deterministic():
    ids = [f"t.py::test_a[{i}]" for i in range(10)] + ["t.py::test_b"]
    got = params.sample(ids, 3)
    assert got == params.sample(ids, 3)
    assert len([g for g in got if "test_a" in g]) == 3 and "t.py::test_b" in got
    assert "t.py::test_a[0]" in got and "t.py::test_a[9]" in got


def git(repo, *a):
    subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True, stdin=subprocess.DEVNULL)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "helper.py").write_text("def f():\n    return 1\n")
    (tmp_path / "test_old.py").write_text("from helper import f\n\ndef test_old():\n    assert f() == 1\n")
    (tmp_path / "test_unrelated.py").write_text("def test_u():\n    assert True\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "base")
    git(tmp_path, "checkout", "-qb", "feature")
    return tmp_path


def commit(repo):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "change")


def test_selection_covers_changed_tests_and_importers_of_changed_helpers(repo):
    (repo / "helper.py").write_text("def f():\n    return 1  # edit\n")
    (repo / "test_new.py").write_text("def test_new():\n    assert True\n")
    commit(repo)
    chosen = select.affected_tests(select.changed_files("main", repo), repo)
    assert chosen["test_new.py"] == "changed"
    assert chosen["test_old.py"].startswith("imports helper")
    assert "test_unrelated.py" not in chosen


def test_gate_catches_flaky_and_passes_stable(repo, tmp_path):
    counter = tmp_path / "counter.txt"
    (repo / "test_flaky.py").write_text(textwrap.dedent(f"""\
        from pathlib import Path
        def test_flaky():
            p = Path({str(counter)!r})
            n = int(p.read_text()) if p.exists() else 0
            p.write_text(str(n + 1))
            assert n % 3 != 2   # fails on every 3rd run
        """))
    (repo / "test_stable.py").write_text("def test_stable():\n    assert True\n")
    commit(repo)
    rc = cli.main(["check", "--base", "main", "--repo", str(repo), "-n", "6", "--python", sys.executable, "--json"])
    assert rc == 1


def test_gate_passes_when_all_stable(repo):
    (repo / "test_stable.py").write_text("def test_stable():\n    assert True\n")
    commit(repo)
    assert cli.main(["check", "--base", "main", "--repo", str(repo), "-n", "3", "--python", sys.executable]) == 0


def test_no_changes_is_ok(repo):
    assert cli.main(["check", "--base", "main", "--repo", str(repo)]) == 0
