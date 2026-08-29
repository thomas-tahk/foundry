#!/usr/bin/env python3
"""Stage 3 of the L0 census: upsert one Resume issue per repo.

Reads the Markdown bodies Stage 2 wrote to census/out/<repo>.md and publishes
each as a labelled GitHub issue, edited in place. Idempotent by title: a repo
never accumulates a second Resume issue.
"""
import json
import subprocess
import sys
from pathlib import Path

from scripts.generate_report import OWNER, load_repos

LABEL = "factory:resume"


def issue_title(repo):
    return f"▶ Resume here — {repo}"


def pick_existing_issue(issues, repo):
    """The number of this repo's Resume issue, open or closed, or None.

    Lowest number wins. GitHub's issue-list endpoint lags creation by a second
    or two, so two runs close together can both create one; picking the oldest
    deterministically makes every later run converge on the same issue.
    """
    title = issue_title(repo)
    matches = sorted(i["number"] for i in issues if i.get("title") == title)
    return matches[0] if matches else None


def duplicate_issues(issues, repo, keep):
    """Open Resume issues for this repo other than the one we are keeping."""
    title = issue_title(repo)
    return sorted(i["number"] for i in issues
                  if i.get("title") == title
                  and i["number"] != keep
                  and str(i.get("state", "")).lower() == "open")


def run(args, **kwargs):
    """Run a gh command, raising on failure so the workflow fails loudly."""
    result = subprocess.run(args, text=True, capture_output=True, **kwargs)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:4])} failed: {result.stderr.strip()}")
    return result


def existing_issues(repo):
    result = run(["gh", "issue", "list", "--repo", f"{OWNER}/{repo}",
                  "--state", "all", "--label", LABEL, "--limit", "50",
                  "--json", "number,title,state"])
    return json.loads(result.stdout or "[]")


def ensure_label(repo):
    """Create the label if absent; a repeat run is a harmless no-op."""
    result = subprocess.run(["gh", "label", "create", LABEL, "--repo", f"{OWNER}/{repo}",
                             "--color", "1D76DB", "--description",
                             "The single pinned Resume issue, rewritten weekly by L0"],
                            text=True, capture_output=True)
    if result.returncode != 0 and "already exists" not in result.stderr:
        raise RuntimeError(f"label create failed for {repo}: {result.stderr.strip()}")


def publish(repo, body):
    ensure_label(repo)
    issues = existing_issues(repo)
    number = pick_existing_issue(issues, repo)
    if number is None:
        run(["gh", "issue", "create", "--repo", f"{OWNER}/{repo}",
             "--title", issue_title(repo), "--label", LABEL, "--body", body])
        print(f"- {repo}: created")
        return
    run(["gh", "issue", "edit", str(number), "--repo", f"{OWNER}/{repo}", "--body", body])
    subprocess.run(["gh", "issue", "reopen", str(number), "--repo", f"{OWNER}/{repo}"],
                   text=True, capture_output=True)
    print(f"- {repo}: updated #{number}")
    for extra in duplicate_issues(issues, repo, number):
        run(["gh", "issue", "close", str(extra), "--repo", f"{OWNER}/{repo}",
             "--comment", f"Duplicate Resume issue. The canonical one is #{number}."])
        print(f"- {repo}: closed duplicate #{extra}")


def main():
    out_dir = Path("census/out")
    if not out_dir.exists():
        sys.exit("census/out does not exist — Stage 2 wrote nothing. Failing loudly.")
    published = 0
    for repo in load_repos():
        path = out_dir / f"{repo}.md"
        if not path.exists():
            print(f"- {repo}: SKIPPED, no narrative written")
            continue
        body = path.read_text().strip()
        if len(body) < 100:
            print(f"- {repo}: SKIPPED, narrative too short to be real ({len(body)} chars)")
            continue
        publish(repo, body)
        published += 1
    print(f"Published {published} Resume issue(s)")
    if published == 0:
        sys.exit("No issues published — treating as failure so the badge does not lie.")


if __name__ == "__main__":
    main()
