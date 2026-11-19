import pandas as pd

from spacepulse import health


def test_classify_known_stages():
    assert health.classify("RUNNING") == "healthy"
    assert health.classify("running") == "healthy"
    assert health.classify("SLEEPING") == "idle"
    assert health.classify("PAUSED") == "idle"
    assert health.classify("BUILDING") == "transitional"
    for stage in ("RUNTIME_ERROR", "BUILD_ERROR", "CONFIG_ERROR", "NO_APP_FILE"):
        assert health.classify(stage) == "broken"


def test_classify_unknown_and_api_failures():
    assert health.classify(None) == "unknown"
    assert health.classify(float("nan")) == "unknown"
    assert health.classify("ERROR_HfHubHTTPError") == "unknown"
    assert health.classify("SOMETHING_NEW") == "unknown"

COLUMNS = ["id", "likes", "stage"]


def make_df(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


def test_add_status_adds_column():
    df = make_df([("a/one", 1, "RUNNING"), ("a/two", 2, "RUNTIME_ERROR")])
    assert health.add_status(df)["status"].tolist() == ["healthy", "broken"]
    assert "status" not in df.columns  # the input is not modified


def test_summarize_counts_and_percentage():
    df = make_df([
        ("a/one", 100, "RUNNING"),
        ("a/two", 50, "RUNTIME_ERROR"),
        ("a/three", 300, "BUILD_ERROR"),
        ("a/four", 10, "SLEEPING"),
        ("a/five", 5, "ERROR_Timeout"),
    ])
    s = health.summarize(df)
    assert s["total"] == 5
    assert s["counts"]["broken"] == 2
    assert s["counts"]["unknown"] == 1
    assert s["broken_pct"] == 50.0  # 2 of the 4 known Spaces
    assert s["top_broken"]["id"].tolist() == ["a/three", "a/two"]


def test_summarize_no_broken():
    s = health.summarize(make_df([("a/one", 1, "RUNNING")]))
    assert s["broken_pct"] == 0.0
    assert s["top_broken"].empty