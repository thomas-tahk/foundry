#!/usr/bin/env python3
"""Stage 1 of the L0 census: gather facts, make no judgments.

Writes census/facts.json. Every value here is mechanically derived from the
GitHub REST API — no model is involved, so this stage is cheap, deterministic,
and unit-testable. The narrative is Stage 2's job.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from scripts.generate_report import OWNER, gh, load_repos

INTENT_NAMES = ("README.md", "VISION.md", "CONTEXT.md", "ROADMAP.md", "CLAUDE.md")
INTENT_DIRS = ("docs/superpowers/specs/", "docs/superpowers/plans/", "docs/adr/")
SKIP_DIRS = ("node_modules/", "dist/", "vendor/", ".git/")
MAX_INTENT_DOCS = 12


def age_in_days(iso_timestamp, now):
    """Whole days between an ISO-8601 timestamp and now; None if absent."""
    if not iso_timestamp:
        return None
    stamp = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    return (now - stamp).days


def detect_test_command(paths, package_json):
    """The command that runs this repo's tests, or None if it has none."""
    if any(p == "go.mod" or p.endswith("/go.mod") for p in paths):
        return "go test ./..."
    if "package.json" in paths and package_json.get("scripts", {}).get("test"):
        return "npm test"
    if any(p in ("pytest.ini", "pyproject.toml", "tox.ini") for p in paths):
        return "pytest"
    return None


def pick_intent_docs(paths):
    """Documents that state what a project is for, capped so prompts stay small."""
    picked = []
    for path in paths:
        if any(skip in path for skip in SKIP_DIRS):
            continue
        name = path.rsplit("/", 1)[-1]
        if name in INTENT_NAMES or path.startswith(INTENT_DIRS):
            picked.append(path)
    return picked[:MAX_INTENT_DOCS]


def stranded_branches(comparisons, pr_heads, now):
    """Branches ahead of the default branch with no open PR pointing at them."""
    out = []
    for name, cmp_data in comparisons.items():
        if name in pr_heads or cmp_data.get("ahead_by", 0) <= 0:
            continue
        out.append({
            "name": name,
            "ahead_by": cmp_data["ahead_by"],
            "last_commit_date": cmp_data["last_commit_date"][:10],
            "age_days": age_in_days(cmp_data["last_commit_date"], now),
        })
    return sorted(out, key=lambda b: b["age_days"] or 0, reverse=True)


def repo_facts(repo, now):
    info = gh(f"/repos/{OWNER}/{repo}")
    if not isinstance(info, dict) or not info.get("default_branch"):
        return {"repo": repo, "default_branch": None, "days_since_last_commit": None,
                "last_commit": None, "open_prs": [], "stranded_branches": [],
                "intent_docs": [], "test_command": None}
    default = info["default_branch"]

    head = gh(f"/repos/{OWNER}/{repo}/commits", {"sha": default, "per_page": 1})
    last_commit = None
    days_since = None
    if isinstance(head, list) and head:
        commit = head[0].get("commit", {})
        date = commit.get("author", {}).get("date", "")
        last_commit = {"sha": head[0]["sha"][:7], "date": date[:10],
                       "subject": (commit.get("message", "") or "").splitlines()[0]}
        days_since = age_in_days(date, now)

    prs_raw = gh(f"/repos/{OWNER}/{repo}/pulls", {"state": "open", "per_page": 100})
    open_prs, pr_heads = [], set()
    if isinstance(prs_raw, list):
        for pr in prs_raw:
            head_ref = pr.get("head", {}).get("ref", "")
            pr_heads.add(head_ref)
            open_prs.append({"number": pr["number"], "title": pr["title"],
                             "draft": bool(pr.get("draft")), "head": head_ref,
                             "age_days": age_in_days(pr.get("created_at", ""), now)})

    branches = gh(f"/repos/{OWNER}/{repo}/branches", {"per_page": 100})
    comparisons = {}
    if isinstance(branches, list):
        for branch in branches:
            name = branch["name"]
            if name == default:
                continue
            cmp_data = gh(f"/repos/{OWNER}/{repo}/compare/{default}...{name}")
            if not isinstance(cmp_data, dict) or "ahead_by" not in cmp_data:
                continue
            commits = cmp_data.get("commits") or []
            date = commits[-1]["commit"]["author"]["date"] if commits else ""
            comparisons[name] = {"ahead_by": cmp_data["ahead_by"], "last_commit_date": date}

    tree = gh(f"/repos/{OWNER}/{repo}/git/trees/{default}", {"recursive": "1"})
    paths = [t["path"] for t in tree.get("tree", [])] if isinstance(tree, dict) else []

    package_json = {}
    if "package.json" in paths:
        blob = gh(f"/repos/{OWNER}/{repo}/contents/package.json")
        if isinstance(blob, dict) and blob.get("content"):
            import base64
            try:
                package_json = json.loads(base64.b64decode(blob["content"]))
            except Exception:  # noqa: BLE001 - a malformed manifest is not fatal
                package_json = {}

    return {
        "repo": repo,
        "default_branch": default,
        "days_since_last_commit": days_since,
        "last_commit": last_commit,
        "open_prs": open_prs,
        "stranded_branches": stranded_branches(comparisons, pr_heads, now),
        "intent_docs": pick_intent_docs(paths),
        "test_command": detect_test_command(paths, package_json),
    }


def main():
    now = datetime.now(timezone.utc)
    repos = load_repos()
    print(f"Gathering census facts for {len(repos)} repo(s)")
    facts = []
    for repo in repos:
        print(f"- {repo}")
        facts.append(repo_facts(repo, now))
    Path("census").mkdir(exist_ok=True)
    out = {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "repos": facts}
    Path("census/facts.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote census/facts.json ({len(facts)} repos)")


if __name__ == "__main__":
    main()
