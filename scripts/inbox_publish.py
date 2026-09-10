#!/usr/bin/env python3
"""Publish the one file priority-post reads: inbox/inbox.json.

The factory marks its state with labels. priority-post must not know those label
names — a rename here would silently empty the user's list. So every item carries
the actions available on it *as data*, including which label to apply and which
number to apply it to, and priority-post applies whatever string it is handed.

Two action kinds exist. `apply_label` is a write; `open_url` is a link. There is
deliberately no kind that merges — the one irreversible step stays on GitHub.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.build_facts import APPROVED, BUILDING, BUILT, TRY_AGAIN, labelled
from scripts.census_facts import stranded_branches
from scripts.generate_report import OWNER, gh, load_elected
from scripts.propose_facts import DECLINED, PROPOSED, issues_with_label
from scripts.warm_facts import default_branch_ci

HUB_ROOT = Path(__file__).resolve().parent.parent
OUT = HUB_ROOT / "inbox" / "inbox.json"

# A proposal body is a page of engineering prose. The detail opens inside a
# one-line strip on a phone, so only the opening paragraph goes in, capped.
DETAIL_CHARS = 240
LEAD_IN = re.compile(r"^\*\*[^*]+\*\*\s*[—–-]\s*")
BUILT_PR = "factory:built"
BLOCKED = "factory:blocked"

# A proposal carrying any of these has already been answered. Nothing takes
# `proposed` back off, so the label stays on for the life of the issue.
ANSWERED = {DECLINED, BUILDING, BUILT, BLOCKED}

# priority-post knows these four strings, because they drive colour and order.
# It knows no others, and drops an item carrying one it does not recognise.
ORDER = ["build_failing", "waiting_on_you", "draft_ready", "branch_stranded"]


def summarize_body(body):
    """The first paragraph of an issue body, without its bold lead-in label."""
    if not body:
        return ""
    first = (body.strip().split("\n\n", 1)[0]).strip()
    first = LEAD_IN.sub("", first).strip()
    if len(first) <= DETAIL_CHARS:
        return first
    cut = first[:DETAIL_CHARS].rsplit(" ", 1)[0].rstrip(" ,.;:—-")
    return f"{cut}…"


def _label(key, text, number, value, confirm=False):
    action = {"key": key, "label": text, "kind": "apply_label",
              "number": number, "value": value}
    if confirm:
        action["confirm"] = True
    return action


def _link(key, text, url):
    return {"key": key, "label": text, "kind": "open_url", "value": url}


def undecided(issues):
    """Proposals you have not answered yet.

    Answering adds a label; nothing takes `proposed` off, and priority-post can
    only add labels, never remove them. So the reader has to do the filtering —
    otherwise "Not now" looks like a button that does nothing, and the item you
    just refused is still there on the next refresh.

    Approving is the same trap one step later: the issue keeps `proposed` while
    it builds, so the list offered "Build it" on work that was already built and
    showed the finished draft directly underneath it, under the same title.
    """
    return [i for i in issues
            if not ANSWERED & {l.get("name") for l in i.get("labels", [])}]


def proposal_items(repo, issues):
    """Work the factory has proposed and is waiting on a decision about."""
    return [{
        "id": f"{repo}#{i['number']}",
        "repo": f"{OWNER}/{repo}",
        "number": i["number"],
        "summary": i.get("title", "").strip(),
        "detail": summarize_body(i.get("body")),
        "state": "waiting_on_you",
        "url": i.get("html_url", ""),
        "since": i.get("created_at", ""),
        "actions": [
            _label("approve", "Build it", i["number"], APPROVED),
            _label("decline", "Not now", i["number"], DECLINED, confirm=True),
            _link("read", "Read the plan", i.get("html_url", "")),
        ],
    } for i in issues]


def draft_items(repo, pulls):
    """Draft pull requests the factory opened and has not been told about.

    The retry label lives on the pull request, not on the issue that spawned it,
    which is why every action carries the number it writes to rather than
    inheriting the item's.
    """
    return [{
        "id": f"{repo}!{p['number']}",
        "repo": f"{OWNER}/{repo}",
        "number": p["number"],
        "summary": p.get("title", "").strip(),
        "detail": "A draft is open. Nothing has shipped.",
        "state": "draft_ready",
        "url": p.get("html_url", ""),
        "since": p.get("created_at", ""),
        "actions": [
            _link("review", "Review on GitHub", p.get("html_url", "")),
            _label("retry", "Try again", p["number"], TRY_AGAIN),
        ],
    } for p in pulls]


def failing_build_item(repo, ci, default, since):
    """Friction, not work. There is no button that fixes a red build.

    `since` is when the failing run started, not now. Stamping this item with the
    publish time rewrote the file every hour, so a document whose whole job is to
    say what changed committed a change every run — and the list could not say
    how long the build had been red.
    """
    if ci.get("state") != "failing":
        return None
    names = ", ".join(ci.get("failing", [])) or "the build"
    return {
        "id": f"{repo}~ci",
        "repo": f"{OWNER}/{repo}",
        "number": None,
        "summary": f"The build is failing on {default}",
        "detail": f"Failing: {names}.",
        "state": "build_failing",
        "url": f"https://github.com/{OWNER}/{repo}/actions",
        "since": since,
        "actions": [_link("open", "See what broke",
                          f"https://github.com/{OWNER}/{repo}/actions")],
    }


def stranded_items(repo, branches):
    """Branches ahead of the default with nothing open pointing at them."""
    return [{
        "id": f"{repo}~branch~{b['name']}",
        "repo": f"{OWNER}/{repo}",
        "number": None,
        "summary": f"A branch has been sitting unfinished for {b['age_days']} days",
        "detail": f"{b['name']} is {b['ahead_by']} commits ahead, last touched "
                  f"{b['last_commit_date']}.",
        "state": "branch_stranded",
        "url": f"https://github.com/{OWNER}/{repo}/tree/{b['name']}",
        "since": f"{b['last_commit_date']}T00:00:00Z",
        "actions": [_link("open", "Open the branch",
                          f"https://github.com/{OWNER}/{repo}/tree/{b['name']}")],
    } for b in branches]


def build_inbox(items, generated_at, projects=()):
    """The published document: what needs the user, most pressing first.

    A red build outranks a decision because it blocks everything else in that
    project; a stranded branch is last because it has waited weeks already and
    can wait another hour.
    """
    ordered = sorted(items, key=lambda i: (ORDER.index(i["state"]), i["since"]))
    return {
        "generated_at": generated_at,
        # The projects the factory may raise work in. priority-post offers these
        # and only these when the user asks for something in plain English, so
        # electing a project is still the single switch it has always been.
        "projects": [f"{OWNER}/{p}" for p in projects],
        "items": ordered,
    }


def live_stranded(repo, default, now):
    """Stranded branches as GitHub sees them right now.

    The census computes this too, weekly, and reading its committed file would
    save a compare call per branch. It also published a branch as "sitting
    unfinished for 39 days" a week after it was merged. An inbox that lies gets
    abandoned, so this pays the calls and asks GitHub.
    """
    prs = gh(f"/repos/{OWNER}/{repo}/pulls", {"state": "open", "per_page": 100})
    pr_heads = {p.get("head", {}).get("ref", "") for p in prs} if isinstance(prs, list) else set()

    branches = gh(f"/repos/{OWNER}/{repo}/branches", {"per_page": 100})
    comparisons = {}
    if isinstance(branches, list):
        for branch in branches:
            name = branch["name"]
            if name == default or name in pr_heads:
                continue
            cmp_data = gh(f"/repos/{OWNER}/{repo}/compare/{default}...{name}")
            if not isinstance(cmp_data, dict) or "ahead_by" not in cmp_data:
                continue
            commits = cmp_data.get("commits") or []
            date = commits[-1]["commit"]["author"]["date"] if commits else ""
            comparisons[name] = {"ahead_by": cmp_data["ahead_by"], "last_commit_date": date}

    return stranded_branches(comparisons, pr_heads, now)


def repo_items(repo, now):
    """Everything in one project that wants the user's attention.

    `now` is a datetime: branch ages are computed from it. Timestamps that reach
    the published file are formatted here, at the edge.
    """
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    info = gh(f"/repos/{OWNER}/{repo}")
    default = info.get("default_branch") if isinstance(info, dict) else None
    items = []
    items += proposal_items(repo, undecided(issues_with_label(repo, PROPOSED, "open")))
    items += draft_items(repo, labelled(repo, BUILT_PR, want_pulls=True))
    if default:
        items += stranded_items(repo, live_stranded(repo, default, now))
        ci = default_branch_ci(repo, default)
        failing = failing_build_item(repo, ci, default,
                                     ci.get("failing_since") or stamp)
        if failing:
            items.append(failing)
    return items


def is_unchanged(previous, current):
    """True when only the timestamp moved.

    The inbox refreshes hourly; committing every hour to record that nothing
    happened would bury the commits that mean something. Everything except the
    timestamp is compared — an earlier version checked only the items, so a
    change to any other field silently never reached the published file.
    """
    if not previous:
        return False
    return {k: v for k, v in previous.items() if k != "generated_at"} == {
        k: v for k, v in current.items() if k != "generated_at"
    }


def main():
    now = datetime.now(timezone.utc)
    elected = load_elected()
    items = []
    for repo in elected:
        items += repo_items(repo, now)
    doc = build_inbox(items, now.strftime("%Y-%m-%dT%H:%M:%SZ"), elected)

    previous = None
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text())
        except json.JSONDecodeError:
            previous = None
    if is_unchanged(previous, doc):
        print(f"inbox: {len(doc['items'])} item(s) needing you — unchanged")
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"inbox: {len(doc['items'])} item(s) needing you")


if __name__ == "__main__":
    main()
