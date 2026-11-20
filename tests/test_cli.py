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

def test_upload_creates_public_dataset_and_uploads_file(tmp_path):
    calls = []

    class Api:
        def create_repo(self, repo_id, **kwargs):
            calls.append(("create", repo_id, kwargs))

        def upload_file(self, **kwargs):
            calls.append(("upload", kwargs))

    snapshot = tmp_path / "2026-11-20.csv"
    snapshot.write_text("id,stage\n")
    cli.upload(Api(), snapshot, "me/spacepulse-history")
    assert calls[0][0] == "create"
    assert calls[0][2]["private"] is False
    assert calls[1][1]["path_in_repo"] == "data/2026-11-20.csv"
    assert calls[1][1]["repo_id"] == "me/spacepulse-history"


def test_main_uploads_only_when_asked(tmp_path, monkeypatch):
    uploads = []
    fake = FakeApi({"a/one": "RUNNING"})
    fake.create_repo = lambda repo_id, **kwargs: None
    fake.upload_file = lambda **kwargs: uploads.append(kwargs)
    monkeypatch.setattr(cli, "HfApi", lambda: fake)

    cli.main(["--limit", "1", "--out", str(tmp_path)])
    assert uploads == []  # no --upload, no upload

    cli.main(["--limit", "1", "--out", str(tmp_path), "--upload", "me/hist"])
    assert len(uploads) == 1
    assert uploads[0]["repo_id"] == "me/hist"