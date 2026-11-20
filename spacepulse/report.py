"""Tables for the dashboard, built from the daily snapshot history."""
from spacepulse import health


def latest_snapshot(history):
    """Rows of the most recent date in the history."""
    if history.empty:
        return history
    return history[history["date"] == history["date"].max()]


def _with_url(df):
    out = df.copy()
    out["url"] = "https://huggingface.co/spaces/" + out["id"]
    return out


def sdk_choices(history):
    """Dropdown values: 'all' plus every SDK seen in the latest snapshot."""
    latest = latest_snapshot(history)
    if latest.empty:
        return ["all"]
    return ["all"] + sorted(latest["sdk"].dropna().unique().tolist())


def working_now(history, sdk="all", top=50):
    """Most-liked Spaces that are running in the latest snapshot."""
    latest = health.add_status(latest_snapshot(history))
    ok = latest[latest["status"] == "healthy"]
    if sdk != "all":
        ok = ok[ok["sdk"] == sdk]
    ok = _with_url(ok.sort_values("likes", ascending=False).head(top))
    return ok[["id", "likes", "sdk", "hardware", "url"]].reset_index(drop=True)


def broken_now(history, top=50):
    """Most-liked Spaces in an error state, with how many days each has been broken."""
    latest = health.add_status(latest_snapshot(history))
    bad = latest[latest["status"] == "broken"]
    days = health.days_broken(history)
    bad = bad.merge(days, left_on="id", right_index=True, how="left")
    bad["days_broken"] = bad["days_broken"].fillna(0).astype(int)
    bad = _with_url(bad.sort_values("likes", ascending=False).head(top))
    return bad[["id", "likes", "stage", "days_broken", "url"]].reset_index(drop=True)