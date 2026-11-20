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

def test_changes_newly_broken_and_recovered():
    prev = make_df([("a/one", 1, "RUNNING"), ("a/two", 2, "RUNTIME_ERROR")])
    curr = make_df([("a/one", 1, "RUNTIME_ERROR"), ("a/two", 2, "RUNNING")])
    out = health.changes(prev, curr).set_index("id")
    assert out.loc["a/one", "kind"] == "newly_broken"
    assert out.loc["a/two", "kind"] == "recovered"


def test_changes_other_and_same_status():
    prev = make_df([("a/one", 1, "RUNNING"), ("a/two", 2, "RUNTIME_ERROR")])
    curr = make_df([("a/one", 1, "SLEEPING"), ("a/two", 2, "BUILD_ERROR")])
    out = health.changes(prev, curr).set_index("id")
    assert out.loc["a/one", "kind"] == "other"  # healthy -> idle
    assert "a/two" not in out.index  # still broken, so no change


def test_changes_ignores_new_and_missing_spaces():
    prev = make_df([("a/one", 1, "RUNNING"), ("a/gone", 3, "RUNNING")])
    curr = make_df([("a/one", 1, "RUNNING"), ("a/new", 4, "RUNTIME_ERROR")])
    assert health.changes(prev, curr).empty

HISTORY_COLUMNS = ["date", "id", "likes", "stage"]


def make_history(rows):
    return pd.DataFrame(rows, columns=HISTORY_COLUMNS)


def test_days_broken_counts_consecutive_days():
    history = make_history([
        ("2026-11-15", "a/one", 1, "RUNNING"),
        ("2026-11-16", "a/one", 1, "RUNTIME_ERROR"),
        ("2026-11-17", "a/one", 1, "RUNTIME_ERROR"),
        ("2026-11-15", "a/two", 2, "RUNTIME_ERROR"),
        ("2026-11-16", "a/two", 2, "RUNTIME_ERROR"),
        ("2026-11-17", "a/two", 2, "RUNTIME_ERROR"),
    ])
    out = health.days_broken(history)
    assert out["a/two"] == 3
    assert out["a/one"] == 2
    assert out.index[0] == "a/two"  # longest first


def test_days_broken_ignores_recovered_spaces():
    history = make_history([
        ("2026-11-16", "a/one", 1, "RUNTIME_ERROR"),
        ("2026-11-17", "a/one", 1, "RUNNING"),
    ])
    assert health.days_broken(history).empty


def test_days_broken_skips_unknown_days():
    history = make_history([
        ("2026-11-15", "a/one", 1, "RUNTIME_ERROR"),
        ("2026-11-16", "a/one", 1, "ERROR_Timeout"),  # API failure, says nothing
        ("2026-11-17", "a/one", 1, "RUNTIME_ERROR"),
    ])
    assert health.days_broken(history)["a/one"] == 2


def test_days_broken_empty_history():
    assert health.days_broken(make_history([])).empty