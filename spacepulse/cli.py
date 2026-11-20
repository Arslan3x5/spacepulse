"""Command line entry point: python -m spacepulse"""
import argparse
import datetime as dt
from pathlib import Path

from huggingface_hub import HfApi

from spacepulse import collect, health


def run(api, limit=200, out_dir="data", date=None):
    """Check the most-liked Spaces, save data/<date>.csv and return (DataFrame, path)."""
    date = date or dt.datetime.now(dt.timezone.utc).date().isoformat()
    spaces = list(api.list_spaces(sort="likes", limit=limit, expand=["likes", "sdk"]))
    df = collect.snapshot(spaces, api.get_space_runtime, date=date)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{date}.csv"
    df.to_csv(path, index=False)
    return df, path


def print_summary(df):
    s = health.summarize(df)
    print(f"Checked {s['total']} Spaces: {s['counts']}")
    print(f"Broken: {s['broken_pct']}% of the Spaces with a known state")
    for row in s["top_broken"].itertuples():
        print(f"  {row.likes}  {row.id}  {row.stage}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="spacepulse",
        description="Record the health of the most-liked Hugging Face Spaces.",
    )
    parser.add_argument("--limit", type=int, default=200, help="how many Spaces to check (default 200)")
    parser.add_argument("--out", default="data", help="folder for the CSV snapshot (default: data)")
    args = parser.parse_args(argv)

    print(f"Checking {args.limit} Spaces, this takes about {round(args.limit * 0.35)} seconds...")
    df, path = run(HfApi(), limit=args.limit, out_dir=args.out)
    print(f"Saved {path}")
    print_summary(df)