from types import SimpleNamespace

from spacepulse import collect


def space(space_id, likes=1, sdk="gradio"):
    return SimpleNamespace(id=space_id, likes=likes, sdk=sdk)


def runtime(stage, hardware="cpu-basic"):
    return SimpleNamespace(stage=stage, hardware=hardware)


def no_sleep(_seconds):
    pass


def test_fetch_stage_returns_stage_and_hardware():
    result = collect.fetch_stage(lambda _id: runtime("RUNNING"), "a/one")
    assert result == ("RUNNING", "cpu-basic")


def test_fetch_stage_turns_failures_into_error_stage():
    def broken(_id):
        raise TimeoutError("slow")

    assert collect.fetch_stage(broken, "a/one", sleep=no_sleep) == ("ERROR_TimeoutError", "")


def test_fetch_stage_retries_then_succeeds():
    calls = []

    def flaky(_id):
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("blip")
        return runtime("RUNNING")

    assert collect.fetch_stage(flaky, "a/one", retries=2, sleep=no_sleep)[0] == "RUNNING"
    assert len(calls) == 3


def test_snapshot_builds_dataframe():
    stages = {"a/one": "RUNNING", "a/two": "RUNTIME_ERROR"}
    df = collect.snapshot(
        [space("a/one", 10), space("a/two", 20)],
        lambda space_id: runtime(stages[space_id]),
        date="2026-11-18",
        sleep=no_sleep,
    )
    assert list(df.columns) == collect.COLUMNS
    assert df["stage"].tolist() == ["RUNNING", "RUNTIME_ERROR"]
    assert df["likes"].tolist() == [10, 20]
    assert set(df["date"]) == {"2026-11-18"}


def test_snapshot_continues_after_a_failure():
    def get(space_id):
        if space_id == "a/bad":
            raise ValueError("boom")
        return runtime("RUNNING")

    df = collect.snapshot([space("a/bad"), space("a/ok")], get, date="2026-11-18", sleep=no_sleep)
    assert df["stage"].tolist() == ["ERROR_ValueError", "RUNNING"]