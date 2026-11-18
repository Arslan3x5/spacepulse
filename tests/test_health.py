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