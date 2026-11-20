"""Turn Hugging Face Space runtime stages into health categories."""

import pandas as pd

HEALTHY = {"RUNNING", "RUNNING_BUILDING"}
IDLE = {"SLEEPING", "PAUSED", "STOPPED"}  # not errors: they wake up or were paused
TRANSITIONAL = {"BUILDING", "DELETING"}
BROKEN = {"RUNTIME_ERROR", "BUILD_ERROR", "CONFIG_ERROR", "NO_APP_FILE"}


def classify(stage):
    """Map a raw runtime stage to healthy, idle, transitional, broken or unknown."""
    if not isinstance(stage, str):
        return "unknown"
    stage = stage.strip().upper()
    if stage in HEALTHY:
        return "healthy"
    if stage in IDLE:
        return "idle"
    if stage in TRANSITIONAL:
        return "transitional"
    if stage in BROKEN:
        return "broken"
    return "unknown"  # includes API failures such as ERROR_HfHubHTTPError

def add_status(df):
    """Return a copy of df with a `status` column."""
    out = df.copy()
    out["status"] = out["stage"].map(classify)
    return out


def summarize(df, top=10):
    """Counts per status, the share of broken Spaces, and the most-liked broken ones.

    The broken share ignores `unknown` rows, because a failed API call says
    nothing about the Space itself.
    """
    d = add_status(df)
    counts = d["status"].value_counts().to_dict()
    known = len(d) - counts.get("unknown", 0)
    broken = counts.get("broken", 0)
    top_broken = (
        d[d["status"] == "broken"]
        .sort_values("likes", ascending=False)
        .head(top)[["id", "likes", "stage"]]
        .reset_index(drop=True)
    )
    return {
        "total": len(d),
        "counts": counts,
        "broken_pct": round(100 * broken / known, 1) if known else 0.0,
        "top_broken": top_broken,
    }

def _kind(was, now):
    if now == "broken":
        return "newly_broken"
    if was == "broken" and now in ("healthy", "idle"):
        return "recovered"
    return "other"


def changes(prev, curr):
    """Spaces whose status changed between two snapshots.

    Only Spaces present in both snapshots are compared. `kind` is
    newly_broken, recovered or other.
    """
    before = add_status(prev)[["id", "status"]].rename(columns={"status": "was"})
    after = add_status(curr)[["id", "likes", "status"]].rename(columns={"status": "now"})
    merged = after.merge(before, on="id")
    merged = merged[merged["was"] != merged["now"]].copy()
    merged["kind"] = [_kind(w, n) for w, n in zip(merged["was"], merged["now"])]
    return merged[["id", "likes", "was", "now", "kind"]].reset_index(drop=True)

def days_broken(history):
    """How many consecutive snapshots (days, if collected daily) each Space has been broken.

    Snapshots with an unknown status (for example an API failure) are skipped,
    because they say nothing about the Space. Returns a Series indexed by Space
    id, longest first. Spaces that are not broken in their latest known
    snapshot are left out.
    """
    h = add_status(history)
    h = h[h["status"] != "unknown"].sort_values(["id", "date"])
    result = {}
    for space_id, group in h.groupby("id"):
        streak = 0
        for status in reversed(group["status"].tolist()):
            if status != "broken":
                break
            streak += 1
        if streak:
            result[space_id] = streak
    return pd.Series(result, name="days_broken", dtype="int64").sort_values(ascending=False)