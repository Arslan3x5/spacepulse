"""Turn Hugging Face Space runtime stages into health categories."""

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