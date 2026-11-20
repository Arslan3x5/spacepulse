from types import SimpleNamespace

import pandas as pd

from spacepulse import cli


class FakeApi:
    """Stands in for HfApi so the tests need no network."""

    def __init__(self, stages):
        self.stages = stages
        self.list_kwargs = None

    def list_spaces(self, **kwargs):
        self.list_kwargs = kwargs
        return [SimpleNamespace(id=i, likes=10, sdk="gradio") for i in self.stages]

    def get_space_runtime(self, space_id):
        return SimpleNamespace(stage=self.stages[space_id], hardware="cpu-basic")


def test_run_saves_csv_and_returns_dataframe(tmp_path):
    api = FakeApi({"a/one": "RUNNING", "a/two": "RUNTIME_ERROR"})
    df, path = cli.run(api, limit=2, out_dir=tmp_path, date="2026-11-18")
    assert path == tmp_path / "2026-11-18.csv"
    saved = pd.read_csv(path)
    assert saved["id"].tolist() == ["a/one", "a/two"]
    assert saved["stage"].tolist() == ["RUNNING", "RUNTIME_ERROR"]
    assert len(df) == 2


def test_run_asks_for_the_most_liked_spaces(tmp_path):
    api = FakeApi({"a/one": "RUNNING"})
    cli.run(api, limit=5, out_dir=tmp_path, date="2026-11-18")
    assert api.list_kwargs["sort"] == "likes"
    assert api.list_kwargs["limit"] == 5


def test_main_prints_summary(tmp_path, monkeypatch, capsys):
    fake = FakeApi({"a/one": "RUNNING", "a/two": "RUNTIME_ERROR"})
    monkeypatch.setattr(cli, "HfApi", lambda: fake)
    cli.main(["--limit", "2", "--out", str(tmp_path)])
    output = capsys.readouterr().out
    assert "Broken: 50.0%" in output
    assert "a/two" in output