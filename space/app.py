import os
import time

import gradio as gr
import pandas as pd
import spaces
from huggingface_hub import HfApi, hf_hub_download

from spacepulse import health, report

DATASET_REPO = os.getenv("DATASET_REPO", "arslan3x5/spacepulse-history")
DAYS_LOADED = 60
CACHE_SECONDS = 3600

ABOUT = f"""
**What this shows.** Every day a GitHub Action checks the runtime state of the 200
most-liked Hugging Face Spaces and saves it to an open dataset.

- **Working now:** Spaces whose state is *running* in the latest snapshot.
- **Broken now:** Spaces in an error state (runtime error, build error, config
  error or no app file), with the number of consecutive daily snapshots they have
  been broken. A new tracker starts at 1 and the number grows each day.
- Sleeping or paused Spaces are not counted as broken: they wake up when visited
  or were paused by their owner.

Some Spaces may be broken on purpose or replaced by a newer version, so treat the
list as a starting point, not a verdict.

Data: [{DATASET_REPO}](https://huggingface.co/datasets/{DATASET_REPO}) |
Code: [github.com/Arslan3x5/spacepulse](https://github.com/Arslan3x5/spacepulse)
"""

_cache = {"time": 0.0, "df": None}


@spaces.GPU
def _gpu_stub():
    """No-op. ZeroGPU Spaces need one @spaces.GPU function at startup."""
    return True


def get_history():
    """Load the latest daily snapshots from the dataset (cached for an hour)."""
    if _cache["df"] is not None and time.time() - _cache["time"] < CACHE_SECONDS:
        return _cache["df"]
    files = sorted(
        f
        for f in HfApi().list_repo_files(DATASET_REPO, repo_type="dataset")
        if f.startswith("data/") and f.endswith(".csv")
    )[-DAYS_LOADED:]
    if not files:
        raise gr.Error("No snapshots yet. The first daily run has not happened.")
    frames = [pd.read_csv(hf_hub_download(DATASET_REPO, f, repo_type="dataset")) for f in files]
    df = pd.concat(frames, ignore_index=True)
    _cache.update(time=time.time(), df=df)
    return df


def linked(df):
    """Turn the id column into a clickable link and drop the url column."""
    out = df.copy()
    out["id"] = "[" + out["id"] + "](" + out["url"] + ")"
    return out.drop(columns="url")


def headline():
    df = get_history()
    summary = health.summarize(report.latest_snapshot(df))
    broken = summary["counts"].get("broken", 0)
    return (
        f"**{broken} of the {summary['total']} most-liked Spaces** are in an error state "
        f"(checked {df['date'].max()}, {df['date'].nunique()} day(s) of history)."
    )


def show_working(sdk, top):
    return linked(report.working_now(get_history(), sdk, int(top)))


def show_broken(top):
    return linked(report.broken_now(get_history(), int(top)))


def sdk_options():
    return gr.Dropdown(choices=report.sdk_choices(get_history()), value="all")


def build_demo():
    with gr.Blocks(title="SpacePulse") as demo:
        gr.Markdown("# SpacePulse\nHealth history for the most-liked Hugging Face Spaces.")
        status = gr.Markdown()
        with gr.Tab("Working now"):
            sdk = gr.Dropdown(choices=["all"], value="all", label="SDK")
            top = gr.Slider(10, 200, value=50, step=10, label="Rows")
            working = gr.Dataframe(datatype=["markdown", "number", "str", "str"], interactive=False)
        with gr.Tab("Broken now"):
            top_b = gr.Slider(10, 200, value=50, step=10, label="Rows")
            broken = gr.Dataframe(datatype=["markdown", "number", "str", "number"], interactive=False)
        with gr.Tab("About"):
            gr.Markdown(ABOUT)

        demo.load(headline, None, status)
        demo.load(sdk_options, None, sdk)
        demo.load(show_working, [sdk, top], working)
        demo.load(show_broken, [top_b], broken)
        sdk.change(show_working, [sdk, top], working)
        top.change(show_working, [sdk, top], working)
        top_b.change(show_broken, [top_b], broken)
    return demo


if __name__ == "__main__":
    build_demo().launch()