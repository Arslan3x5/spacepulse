import pandas as pd

from spacepulse import report

COLUMNS = ["date", "id", "likes", "sdk", "stage", "hardware"]


def make_history(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


def sample():
    return make_history([
        ("2026-11-19", "a/one", 100, "gradio", "RUNTIME_ERROR", "cpu-basic"),
        ("2026-11-19", "a/two", 50, "docker", "RUNNING", "cpu-basic"),
        ("2026-11-19", "a/three", 30, "gradio", "RUNNING", "zero-a10g"),
        ("2026-11-20", "a/one", 100, "gradio", "RUNTIME_ERROR", "cpu-basic"),
        ("2026-11-20", "a/two", 50, "docker", "RUNNING", "cpu-basic"),
        ("2026-11-20", "a/three", 30, "gradio", "BUILD_ERROR", "zero-a10g"),
        ("2026-11-20", "a/four", 500, "gradio", "SLEEPING", "cpu-basic"),
    ])


def test_latest_snapshot_keeps_only_the_newest_date():
    latest = report.latest_snapshot(sample())
    assert set(latest["date"]) == {"2026-11-20"}
    assert len(latest) == 4


def test_working_now_lists_only_running_spaces():
    out = report.working_now(sample())
    assert out["id"].tolist() == ["a/two"]
    assert out["url"].tolist() == ["https://huggingface.co/spaces/a/two"]


def test_working_now_filters_by_sdk():
    assert report.working_now(sample(), sdk="docker")["id"].tolist() == ["a/two"]
    assert report.working_now(sample(), sdk="gradio").empty


def test_broken_now_counts_days_and_sorts_by_likes():
    out = report.broken_now(sample())
    assert out["id"].tolist() == ["a/one", "a/three"]
    assert out["days_broken"].tolist() == [2, 1]


def test_sdk_choices():
    assert report.sdk_choices(sample()) == ["all", "docker", "gradio"]


def test_empty_history_is_safe():
    empty = make_history([])
    assert report.working_now(empty).empty
    assert report.broken_now(empty).empty
    assert report.sdk_choices(empty) == ["all"]