"""Publish the dashboard in space/ to the Hugging Face Space.

Usage (PowerShell):
    $env:HF_TOKEN = "<write token>"
    python scripts/deploy_space.py
"""
import os
import sys

from huggingface_hub import HfApi

SPACE_ID = os.getenv("SPACE_ID", "arslan3x5/spacepulse")


def main():
    token = os.getenv("HF_TOKEN")
    if not token:
        sys.exit("Set HF_TOKEN to a Hugging Face write token first.")
    HfApi(token=token).upload_folder(
        folder_path="space",
        repo_id=SPACE_ID,
        repo_type="space",
        commit_message="Deploy dashboard",
    )
    print(f"Done: https://huggingface.co/spaces/{SPACE_ID}")


if __name__ == "__main__":
    main()