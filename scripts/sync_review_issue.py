#!/usr/bin/env python3
"""Mirror a War Room review watchdog report to one deduplicated GitHub Issue.

Designed to run only in the scheduled workflow after validation; no secrets
other than the short-lived built-in GITHUB_TOKEN are ever required.
"""
import argparse
import json
import os
import subprocess
from pathlib import Path

TITLE = "[War Room] Curated intelligence review due"


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True).strip()


def sync(repo: str, needs_review: bool, report_path: Path):
    issues = json.loads(gh("issue", "list", "--repo", repo, "--state", "all", "--limit", "100", "--json", "number,title,state"))
    matches = [x for x in issues if x["title"] == TITLE]
    if len(matches) > 1:
        raise RuntimeError("Multiple matching review issues found; refusing ambiguous update")
    existing = matches[0] if matches else None
    if needs_review:
        if existing:
            gh("issue", "edit", str(existing["number"]), "--repo", repo, "--body-file", str(report_path))
            if existing["state"] != "OPEN":
                gh("issue", "reopen", str(existing["number"]), "--repo", repo)
            print(f"Updated review issue #{existing['number']}")
        else:
            url = gh("issue", "create", "--repo", repo, "--title", TITLE, "--body-file", str(report_path))
            print(f"Opened review issue {url}")
    elif existing and existing["state"] == "OPEN":
        gh("issue", "close", str(existing["number"]), "--repo", repo, "--comment", "Current editorial review dates and scheduled deadlines are within the published limits. This does not assert that any external source was checked.")
        print(f"Closed now-clear review issue #{existing['number']}")
    else:
        print("No review due; no issue update needed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--needs-review", required=True, choices=("true", "false"))
    parser.add_argument("--markdown-file", required=True, type=Path)
    args = parser.parse_args()
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not repo or not os.getenv("GH_TOKEN"):
        raise SystemExit("GITHUB_REPOSITORY and GH_TOKEN must be set in the workflow")
    sync(repo, args.needs_review == "true", args.markdown_file)


if __name__ == "__main__":
    main()