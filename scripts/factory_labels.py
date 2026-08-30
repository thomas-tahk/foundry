#!/usr/bin/env python3
"""Create the factory label vocabulary in every elected repo.

L2 fires on `issues.labeled`, which means the label has to exist before the
user can apply it. Run this once per newly elected repo; a repeat run is a
no-op. Idempotent by design — `gh label create` on an existing label is not an
error worth failing a run over.
"""
import subprocess
import sys

from scripts.generate_report import OWNER, load_elected

# Colour and description are documentation the user reads on a phone, in the
# label picker, at the moment of approving work. They are not decoration.
VOCABULARY = [
    ("factory:resume", "1D76DB", "The single pinned Resume issue, rewritten weekly by L0"),
    ("factory:proposed", "0E8A16", "Proposed work awaiting a decision"),
    ("factory:approved", "5319E7", "Approved — L2 builds this into a draft PR"),
    ("factory:building", "FBCA04", "L2 is building this now"),
    ("factory:declined", "B60205", "Never propose this again"),
    ("factory:blocked", "D93F0B", "Needs something only you can supply"),
    ("factory:deep", "000000", "Escalate this one issue to a stronger model"),
]


def ensure_label(repo, name, color, description):
    """Create the label, or bring an existing one up to date. Returns an action."""
    created = subprocess.run(
        ["gh", "label", "create", name, "--repo", f"{OWNER}/{repo}",
         "--color", color, "--description", description],
        text=True, capture_output=True)
    if created.returncode == 0:
        return "created"
    if "already exists" not in created.stderr:
        raise RuntimeError(f"{repo}/{name}: {created.stderr.strip()}")
    edited = subprocess.run(
        ["gh", "label", "edit", name, "--repo", f"{OWNER}/{repo}",
         "--color", color, "--description", description],
        text=True, capture_output=True)
    if edited.returncode != 0:
        raise RuntimeError(f"{repo}/{name}: {edited.stderr.strip()}")
    return "updated"


def main():
    repos = load_elected()
    if not repos:
        print("elected.txt is empty; no repos to label.")
        return
    print(f"Ensuring {len(VOCABULARY)} labels in {len(repos)} elected repo(s)")
    for repo in repos:
        actions = [ensure_label(repo, *label) for label in VOCABULARY]
        created = actions.count("created")
        print(f"- {repo}: {created} created, {len(actions) - created} already present")


if __name__ == "__main__":
    main()
