#!/usr/bin/env python3
"""Stage 1 of the builder: pick the one piece of work this run will build.

Writes build/facts.json. No model runs unless there is work, so an idle poll
costs a few API calls and exits.

Two kinds of work, in priority order:

1. A pull request the user labelled `factory:try-again` — they have already read
   an attempt and said what is wrong, so finishing it beats starting something new.
2. An issue labelled `factory:approved`.

The retry attempt counter lives in a hidden marker in the PR body rather than in
commit archaeology, and the cap is refused here so a doomed request never starts
a model.
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.generate_report import OWNER, gh, load_elected
from scripts.propose_facts import extract_source

APPROVED = "factory:approved"
TRY_AGAIN = "factory:try-again"
BUILDING = "factory:building"
DEEP = "factory:deep"
MAX_ATTEMPTS = 3

# Stage 3 stamps every comment it writes with this. The token that posts them is
# the user's own, so a factory comment is indistinguishable from a human one by
# author alone — and feeding its own words back as instructions is a documented
# way to build a loop that never settles.
FACTORY_MARK = "<!-- factory -->"
ATTEMPT_RE = re.compile(r"<!--\s*attempt:\s*(\d+)\s*-->", re.I)
SLUG_NOISE_RE = re.compile(r"[^a-z0-9]+")


def slugify(title, limit=40):
    """A branch-safe fragment of an issue title."""
    slug = SLUG_NOISE_RE.sub("-", (title or "").lower()).strip("-")
    return slug[:limit].strip("-") or "task"


def attempt_count(pr_body):
    """How many attempts this PR already carries. An unmarked PR is attempt 1."""
    match = ATTEMPT_RE.search(pr_body or "")
    return int(match.group(1)) if match else 1


def labelled(repo, label, want_pulls):
    """Open issues (or PRs) carrying a label. The issues endpoint returns both."""
    result = gh(f"/repos/{OWNER}/{repo}/issues",
                {"labels": label, "state": "open", "per_page": 100})
    if not isinstance(result, list):
        return []
    return [i for i in result if ("pull_request" in i) == want_pulls]


def human_comments(repo, number):
    """The comments a person wrote, newest last. Bots and our own are dropped."""
    result = gh(f"/repos/{OWNER}/{repo}/issues/{number}/comments", {"per_page": 100})
    if not isinstance(result, list):
        return []
    kept = []
    for comment in result:
        body = comment.get("body") or ""
        author = comment.get("user") or {}
        if author.get("type") == "Bot" or author.get("login", "").endswith("[bot]"):
            continue
        if FACTORY_MARK in body:
            continue
        kept.append({"author": author.get("login", "?"),
                     "written_at": comment.get("created_at", ""),
                     "body": body.strip()})
    return kept


def gh_write(args):
    """A gh mutation, raising with stderr so the workflow fails loudly."""
    result = subprocess.run(["gh", *args], text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {result.stderr.strip()}")


def refuse_further_attempts(repo, pr):
    """Stop asking. Say so on the PR and take the request label back off."""
    number = str(pr["number"])
    gh_write(["issue", "comment", number, "--repo", f"{OWNER}/{repo}", "--body",
              f"{FACTORY_MARK}\nThis is the fourth request on the same pull request, "
              f"and {MAX_ATTEMPTS} attempts is the limit. Three tries that all missed "
              "usually means the task itself is underspecified rather than the attempt "
              "being unlucky.\n\nWhat would help: say which single change would make "
              "this mergeable, or close this and open a narrower task."])
    gh_write(["pr", "edit", number, "--repo", f"{OWNER}/{repo}",
              "--remove-label", TRY_AGAIN])


def retry_work(repo, pr):
    """A retry, or None when the attempt cap refuses it."""
    attempts = attempt_count(pr.get("body", ""))
    if attempts >= MAX_ATTEMPTS:
        print(f"- {repo}: PR #{pr['number']} has had {attempts} attempts — refusing")
        refuse_further_attempts(repo, pr)
        return None
    issue = linked_issue(repo, pr.get("body", ""))
    return {
        "repo": repo,
        "kind": "retry",
        "pr_number": pr["number"],
        # The issues endpoint knows a PR exists but not which branch it is on.
        "branch": head_branch(repo, pr["number"]),
        "attempt": attempts + 1,
        "issue_number": issue.get("number"),
        "issue_title": issue.get("title", pr.get("title", "")),
        "issue_body": issue.get("body", ""),
        "premise_cited": bool(extract_source(issue.get("body", ""))),
        "feedback": human_comments(repo, pr["number"]),
        "deep": has_label(pr, DEEP) or has_label(issue, DEEP),
    }


def head_branch(repo, number):
    detail = gh(f"/repos/{OWNER}/{repo}/pulls/{number}")
    if not isinstance(detail, dict):
        return ""
    return (detail.get("head") or {}).get("ref", "")


CLOSES_RE = re.compile(r"\bcloses\s+#(\d+)", re.I)


def linked_issue(repo, pr_body):
    """The issue a factory PR closes, so a retry rebuilds against the real task."""
    match = CLOSES_RE.search(pr_body or "")
    if not match:
        return {}
    found = gh(f"/repos/{OWNER}/{repo}/issues/{match.group(1)}")
    return found if isinstance(found, dict) else {}


def has_label(item, name):
    return any(l.get("name") == name for l in (item or {}).get("labels", []))


def build_work(repo, issue):
    """A first build from an approved issue."""
    return {
        "repo": repo,
        "kind": "build",
        "pr_number": None,
        "branch": f"claude/issue-{issue['number']}-{slugify(issue.get('title'))}",
        "attempt": 1,
        "issue_number": issue["number"],
        "issue_title": issue.get("title", ""),
        "issue_body": issue.get("body", ""),
        # A proposal this factory wrote carries a hidden origin marker; one the
        # user typed by hand does not. The builder verifies its own premises and
        # stands down on the user's, who does not have to cite evidence to
        # themselves.
        "premise_cited": bool(extract_source(issue.get("body", ""))),
        "feedback": [],
        "deep": has_label(issue, DEEP),
    }


def find_work(repos):
    """The single unit of work for this run, or None."""
    for repo in repos:
        for pr in labelled(repo, TRY_AGAIN, want_pulls=True):
            work = retry_work(repo, pr)
            if work:
                return work
    for repo in repos:
        for issue in labelled(repo, APPROVED, want_pulls=False):
            if has_label(issue, BUILDING):
                continue
            return build_work(repo, issue)
    return None


def main():
    repos = load_elected()
    print(f"Checking {len(repos)} elected project(s) for work")
    work = find_work(repos)
    Path("build").mkdir(exist_ok=True)
    payload = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "work": work}
    Path("build/facts.json").write_text(json.dumps(payload, indent=2) + "\n")
    if not work:
        print("Nothing to build.")
        return
    what = (f"retry attempt {work['attempt']} on {work['repo']}#{work['pr_number']}"
            if work["kind"] == "retry"
            else f"{work['repo']}#{work['issue_number']} — {work['issue_title']}")
    print(f"Building: {what}")


if __name__ == "__main__":
    sys.exit(main())
