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