"""Collect runtime snapshots of Hugging Face Spaces."""
import datetime as dt
import time

import pandas as pd

COLUMNS = ["date", "id", "likes", "sdk", "stage", "hardware"]


def _text(value):
    value = getattr(value, "value", value)  # works for plain strings and enums
    return "" if value is None else str(value)


def fetch_stage(get_runtime, space_id, retries=2, sleep=time.sleep):
    """Return (stage, hardware) for one Space. Never raises.

    A failure after all retries becomes the stage ERROR_<ExceptionName>, which
    health.classify() treats as unknown. `get_runtime` is passed in (for example
    HfApi().get_space_runtime) so tests can use a fake and need no network.
    """
    for attempt in range(retries + 1):
        try:
            runtime = get_runtime(space_id)
            return _text(runtime.stage), _text(runtime.hardware)
        except Exception as exc:
            if attempt == retries:
                return "ERROR_" + type(exc).__name__, ""
            sleep(2**attempt)  # wait 1s, then 2s, before trying again


def snapshot(spaces, get_runtime, date=None, sleep=time.sleep):
    """One row per Space: date, id, likes, sdk, stage, hardware.

    `spaces` is any iterable of objects with id, likes and sdk attributes,
    such as the result of HfApi().list_spaces().
    """
    date = date or dt.datetime.now(dt.timezone.utc).date().isoformat()
    rows = []
    for space in spaces:
        stage, hardware = fetch_stage(get_runtime, space.id, sleep=sleep)
        rows.append(
            {
                "date": date,
                "id": space.id,
                "likes": getattr(space, "likes", None),
                "sdk": getattr(space, "sdk", None),
                "stage": stage,
                "hardware": hardware,
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)