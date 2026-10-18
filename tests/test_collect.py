import json
from pathlib import Path

from stabgate import collect


def test_collect_names_files_with_metadata(tmp_path, monkeypatch):
    def fake_gh(*args):
        if args[0] == "run" and args[1] == "list":
            return json.dumps([{"databaseId": 7, "headSha": "abcdef123456", "headBranch": "feat/x", "conclusion": "success"}])
        if args[0] == "run" and args[1] == "download":
            d = Path(args[args.index("-D") + 1]) / "junit-linux"
            d.mkdir()
            (d / "report.xml").write_text("<testsuites/>")
            return ""
        raise AssertionError(args)

    monkeypatch.setattr(collect, "_gh", fake_gh)
    files = collect.collect("o/r", tmp_path / "out")
    assert [f.name for f in files] == ["7__abcdef1__feat-x__junit-linux.xml"]
