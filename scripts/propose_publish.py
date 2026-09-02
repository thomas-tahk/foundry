#!/usr/bin/env python3
"""Stage 3 of the L1 proposer and of L3 keep-warm: publish one proposal per repo.

Both loops share this publisher, which is how they share one 2-per-repo cap and
one dedupe rather than getting a queue each. L1 writes propose/out/,
L3 writes warm/out/; pass --dir to choose.

Reads the Markdown Stage 2 wrote to <dir>/<repo>.md and opens it as a
`factory:proposed` issue. Every guard Stage 1 applied is re-applied here against
live state: the model has no token and no way to bypass the cap, and a proposal
whose Source is already taken, or whose title the user already declined, is
dropped rather than opened.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from scripts.generate_report import OWNER
from scripts.propose_facts import (
    OPEN_PROPOSAL_CAP,
    PROPOSED,
    extract_source,
    normalize_title,
    repo_proposal_state,
)

TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
LABEL_COLOR = "0E8A16"
LABEL_DESC = "Proposed work awaiting a decision"


def run(args):
    """Run a gh command, raising with stderr so the workflow fails loudly."""
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:4])} failed: {result.stderr.strip()}")
    return result


def ensure_label(repo, label, color, description):
    result = subprocess.run(["gh", "label", "create", label, "--repo", f"{OWNER}/{repo}",
                             "--color", color, "--description", description],
                            text=True, capture_output=True)
    if result.returncode != 0 and "already exists" not in result.stderr:
        raise RuntimeError(f"label create failed for {repo}: {result.stderr.strip()}")


def split_title(markdown):
    """The `# Title` heading and the body beneath it."""
    match = TITLE_RE.search(markdown)
    if not match:
        return None, markdown
    body = markdown[:match.start()] + markdown[match.end():]
    return match.group(1), body.strip()


def rejection(repo, title, source, state):
    """Why this proposal must not be opened, or None if it may be."""
    if not title:
        return "no `# Title` heading"
    if not source:
        return "no `Source:` line — the evidence rule is not optional"
    if state["at_cap"]:
        return f"queue filled to {OPEN_PROPOSAL_CAP} since Stage 1"
    if normalize_title(title) in {normalize_title(d["title"]) for d in state["declined"]}:
        return f"the user declined this work before: {title}"
    if source in state["taken_sources"]:
        return f"source already has an open proposal: {source}"
    return None


def publish_one(path):
    repo = path.stem
    title, body = split_title(path.read_text())
    source = extract_source(body)
    state = repo_proposal_state(repo)

    reason = rejection(repo, title, source, state)
    if reason:
        print(f"- {repo}: dropped — {reason}")
        return False

    ensure_label(repo, PROPOSED, LABEL_COLOR, LABEL_DESC)
    run(["gh", "issue", "create", "--repo", f"{OWNER}/{repo}",
         "--title", title, "--label", PROPOSED, "--body", body])
    print(f"- {repo}: proposed \"{title}\"")
    return True


def parse_args(argv):
    """The directory of proposals to publish. L1 writes one, L3 the other."""
    if len(argv) >= 2 and argv[0] == "--dir":
        return Path(argv[1])
    if argv:
        raise SystemExit(f"usage: {sys.argv[0]} [--dir <path>]")
    return Path("propose/out")


def main():
    out_dir = parse_args(sys.argv[1:])
    paths = sorted(out_dir.glob("*.md")) if out_dir.is_dir() else []
    if not paths:
        # A silent run is the correct outcome when nothing is worth promoting.
        print(f"No proposals in {out_dir}. Nothing to publish.")
        return
    print(f"Publishing {len(paths)} proposal(s)")
    opened = sum(publish_one(p) for p in paths)
    print(f"Opened {opened} of {len(paths)}")


if __name__ == "__main__":
    main()
