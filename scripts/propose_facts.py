#!/usr/bin/env python3
"""Stage 1 of the L1 proposer: decide which repos may receive a proposal.

Writes propose/facts.json. Every value is mechanically derived from the GitHub
REST API. The cap and the duplicate-source check are enforced here and again in
Stage 3 — never by the model, which runs without a token on purpose.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.generate_report import OWNER, gh, load_elected

PROPOSED = "factory:proposed"
DECLINED = "factory:declined"
RESUME = "factory:resume"
OPEN_PROPOSAL_CAP = 2  # shared across L1 and L3, per repo — not 2 each.

SOURCE_RE = re.compile(r"^\s*(?:\*\*)?Source:(?:\*\*)?\s*(.+?)\s*$", re.M | re.I)
STEP_RE = re.compile(r"^\s*(\d+)\.\s+(.*\S)\s*$", re.M)
TITLE_NOISE_RE = re.compile(r"[^a-z0-9]+")


def extract_source(body):
    """The `Source:` line an earlier loop stamped on a proposal, or None."""
    match = SOURCE_RE.search(body or "")
    return match.group(1).strip() if match else None


def normalize_title(title):
    """A proposal title reduced to its content, for comparing two proposals.

    Declines are keyed on this and never on `Source:`. A `Source:` names where a
    proposal came from — a step *number* in the Resume issue, or a branch L3 noticed
    — and both outlive the thing they pointed at. L0 rewrites the Resume issue weekly,
    so "step 2" is a different task most weeks; a stranded branch is one signal behind
    many possible proposals. Keying declines on the origin made one refusal silence
    every later proposal that happened to share it. The title names the work itself.
    """
    return TITLE_NOISE_RE.sub(" ", (title or "").lower()).strip()


def parse_next_steps(body):
    """The numbered steps under `## Next steps` in an L0 Resume issue."""
    if not body:
        return []
    section = re.split(r"^## +Next steps\s*$", body, maxsplit=1, flags=re.M)
    if len(section) < 2:
        return []
    rest = re.split(r"^## ", section[1], maxsplit=1, flags=re.M)[0]
    return [text for _, text in STEP_RE.findall(rest)]


def issues_with_label(repo, label, state):
    result = gh(f"/repos/{OWNER}/{repo}/issues",
                {"labels": label, "state": state, "per_page": 100})
    if not isinstance(result, list):
        return []
    # The issues endpoint returns PRs too; they are not proposals.
    return [i for i in result if "pull_request" not in i]


def repo_proposal_state(repo):
    """What L1 is allowed to do in this repo, and the evidence it may build on."""
    resume = issues_with_label(repo, RESUME, "open")
    proposed = issues_with_label(repo, PROPOSED, "open")
    declined = issues_with_label(repo, DECLINED, "all")

    open_count = len(proposed)
    taken = [s for s in (extract_source(i.get("body", "")) for i in proposed) if s]
    refused = [{"title": i.get("title", ""),
                "source": extract_source(i.get("body", "")) or ""}
               for i in declined]

    steps = parse_next_steps(resume[0].get("body", "")) if resume else []
    at_cap = open_count >= OPEN_PROPOSAL_CAP

    return {
        "repo": repo,
        "resume_issue": resume[0]["number"] if resume else None,
        "next_steps": steps,
        "open_proposals": open_count,
        "cap": OPEN_PROPOSAL_CAP,
        "at_cap": at_cap,
        "taken_sources": taken,
        "declined": refused,
        "eligible": bool(steps) and not at_cap,
        "skip_reason": _skip_reason(steps, at_cap, bool(resume)),
    }


def _skip_reason(steps, at_cap, has_resume):
    if at_cap:
        return f"queue full — {OPEN_PROPOSAL_CAP} open proposals already"
    if not has_resume:
        return "no L0 Resume issue to promote a step from"
    if not steps:
        return "the Resume issue lists no next steps"
    return None


def main():
    now = datetime.now(timezone.utc)
    repos = load_elected()
    print(f"Checking proposal eligibility for {len(repos)} elected repo(s)")
    states = []
    for repo in repos:
        state = repo_proposal_state(repo)
        flag = "eligible" if state["eligible"] else f"skip — {state['skip_reason']}"
        print(f"- {repo}: {flag}")
        states.append(state)
    Path("propose").mkdir(exist_ok=True)
    out = {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "repos": states}
    Path("propose/facts.json").write_text(json.dumps(out, indent=2) + "\n")
    eligible = sum(1 for s in states if s["eligible"])
    print(f"Wrote propose/facts.json ({eligible} of {len(states)} eligible)")


if __name__ == "__main__":
    main()
