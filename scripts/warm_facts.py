#!/usr/bin/env python3
"""Stage 1 of the L3 keep-warm loop: find friction, make no judgments.

Repos go cold when friction accumulates — CI goes red, a branch strands, a
dependency PR sits. L3 keeps re-entry cheap by surfacing that friction while it
is still small. Every signal here is mechanically derived; the narrative and the
choice of which one is worth an issue are Stage 2's job.

Writes warm/facts.json, and reuses L1's eligibility so the two loops share one
2-per-repo cap rather than getting two each.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.census_facts import age_in_days, stranded_branches
from scripts.generate_report import OWNER, gh, load_elected
from scripts.propose_facts import repo_proposal_state

STRANDED_DAYS = 21  # A branch idle this long is the user's dormancy made visible.
DEPENDABOT_DAYS = 14


def default_branch_ci(repo, default):
    """The conclusion of the latest check runs on the default branch."""
    runs = gh(f"/repos/{OWNER}/{repo}/commits/{default}/check-runs", {"per_page": 50})
    if not isinstance(runs, dict):
        return {"state": "unknown", "failing": []}
    check_runs = runs.get("check_runs") or []
    if not check_runs:
        return {"state": "none", "failing": []}
    failing = [c["name"] for c in check_runs
               if c.get("conclusion") in ("failure", "timed_out")]
    if failing:
        return {"state": "failing", "failing": failing}
    if any(c.get("status") != "completed" for c in check_runs):
        return {"state": "in_progress", "failing": []}
    return {"state": "passing", "failing": []}


def stale_dependency_prs(open_prs):
    """Dependabot PRs old enough that the dependency has visibly rotted."""
    return [pr for pr in open_prs
            if pr["head"].startswith("dependabot/")
            and (pr["age_days"] or 0) >= DEPENDABOT_DAYS]


def repo_friction(repo, now):
    info = gh(f"/repos/{OWNER}/{repo}")
    if not isinstance(info, dict) or not info.get("default_branch"):
        return {"repo": repo, "reachable": False}
    default = info["default_branch"]

    prs_raw = gh(f"/repos/{OWNER}/{repo}/pulls", {"state": "open", "per_page": 100})
    open_prs, pr_heads = [], set()
    if isinstance(prs_raw, list):
        for pr in prs_raw:
            head = pr.get("head", {}).get("ref", "")
            pr_heads.add(head)
            open_prs.append({"number": pr["number"], "title": pr["title"],
                             "head": head, "draft": bool(pr.get("draft")),
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

    stranded = [b for b in stranded_branches(comparisons, pr_heads, now)
                if (b["age_days"] or 0) >= STRANDED_DAYS]

    eligibility = repo_proposal_state(repo)
    return {
        "repo": repo,
        "reachable": True,
        "default_branch": default,
        "ci": default_branch_ci(repo, default),
        "stranded_branches": stranded,
        "stale_dependency_prs": stale_dependency_prs(open_prs),
        "open_proposals": eligibility["open_proposals"],
        "at_cap": eligibility["at_cap"],
        "taken_sources": eligibility["taken_sources"],
        "declined": eligibility["declined"],
        "eligible": not eligibility["at_cap"],
    }


def has_friction(state):
    return bool(state.get("stranded_branches")
                or state.get("stale_dependency_prs")
                or state.get("ci", {}).get("state") == "failing")


def main():
    now = datetime.now(timezone.utc)
    repos = load_elected()
    print(f"Checking friction in {len(repos)} elected repo(s)")
    states = []
    for repo in repos:
        state = repo_friction(repo, now)
        if not state.get("reachable"):
            print(f"- {repo}: unreachable")
        elif not state["eligible"]:
            print(f"- {repo}: skip — queue full ({state['open_proposals']} open)")
        elif has_friction(state):
            print(f"- {repo}: friction found")
        else:
            print(f"- {repo}: warm")
        states.append(state)
    Path("warm").mkdir(exist_ok=True)
    out = {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "repos": states}
    Path("warm/facts.json").write_text(json.dumps(out, indent=2) + "\n")
    actionable = sum(1 for s in states if s.get("eligible") and has_friction(s))
    print(f"Wrote warm/facts.json ({actionable} repo(s) with actionable friction)")


if __name__ == "__main__":
    main()
