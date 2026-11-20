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


def upload(api, path, repo_id):
    """Upload one snapshot CSV to a public dataset repo on the Hub."""
    path = Path(path)
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True, private=False)
    api.upload_file(
        path_or_fileobj=str(path),
        path_in_repo=f"data/{path.name}",
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"snapshot {path.stem}",
    )


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
    parser.add_argument("--upload", metavar="REPO", help="also upload the snapshot to this dataset repo, e.g. user/spacepulse-history (needs HF_TOKEN)")
    args = parser.parse_args(argv)

    print(f"Checking {args.limit} Spaces, this takes about {round(args.limit * 0.35)} seconds...")
    api = HfApi()
    df, path = run(api, limit=args.limit, out_dir=args.out)
    print(f"Saved {path}")
    if args.upload:
        upload(api, path, args.upload)
        print(f"Uploaded to https://huggingface.co/datasets/{args.upload}")
    print_summary(df)