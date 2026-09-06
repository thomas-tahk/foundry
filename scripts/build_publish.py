#!/usr/bin/env python3
"""Stage 3 of the builder: commit what the model wrote and open the draft PR.

The model never holds a GitHub token — it edits files under work/<repo>/ and
writes the pull-request text to build/out/<repo>.md. Everything that touches
GitHub happens here, in fixed Python, and is re-checked against live state.

Three outcomes, and only the first one opens a pull request:

* build/out/<repo>.md exists and the tree changed — commit, push, open or update
  the draft PR, and mark the issue built.
* build/notes/<repo>.md exists — the model stopped on purpose (a stale premise, a
  decision only the user can make). Say so on the issue and hand it back.
* neither — the run produced nothing. Say that too. A green workflow badge must
  never imply a task succeeded.
"""
import json
import subprocess
import sys
from pathlib import Path

from scripts.build_facts import APPROVED, BUILDING, FACTORY_MARK, TRY_AGAIN
from scripts.generate_report import OWNER
from scripts.propose_publish import split_title

BUILT = "factory:built"
BLOCKED = "factory:blocked"
FACTS = Path("build/facts.json")


def run(args, cwd=None, check=True):
    """Run a command, raising with stderr so the workflow fails loudly."""
    result = subprocess.run(args, text=True, capture_output=True, cwd=cwd)
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result


def load_work():
    if not FACTS.exists():
        return None
    return json.loads(FACTS.read_text()).get("work")


def tree_changed(repo_dir):
    return bool(run(["git", "status", "--porcelain"], cwd=repo_dir).stdout.strip())


def default_branch(repo):
    result = run(["gh", "repo", "view", f"{OWNER}/{repo}", "--json", "defaultBranchRef",
                  "--jq", ".defaultBranchRef.name"])
    return result.stdout.strip() or "main"


def comment(repo, number, body):
    run(["gh", "issue", "comment", str(number), "--repo", f"{OWNER}/{repo}",
         "--body", f"{FACTORY_MARK}\n{body}"])


def relabel(repo, number, add=(), remove=()):
    """Move an issue's labels. Removing a label it does not carry is not an error."""
    args = ["gh", "issue", "edit", str(number), "--repo", f"{OWNER}/{repo}"]
    for label in add:
        args += ["--add-label", label]
    for label in remove:
        args += ["--remove-label", label]
    run(args)


def hand_back(work, body):
    """Publish nothing. Explain on the issue and release it for the user."""
    number = work["issue_number"] or work["pr_number"]
    comment(work["repo"], number, body)
    if work["issue_number"]:
        relabel(work["repo"], work["issue_number"],
                add=[BLOCKED], remove=[BUILDING, APPROVED])
    if work["pr_number"]:
        run(["gh", "pr", "edit", str(work["pr_number"]), "--repo",
             f"{OWNER}/{work['repo']}", "--remove-label", TRY_AGAIN], check=False)
    print(f"- handed back: {work['repo']}#{number}")


def commit_and_push(work, repo_dir, title):
    """One commit on the task's branch, force-pushed so a retry replaces attempt N-1."""
    branch = work["branch"]
    run(["git", "checkout", "-B", branch], cwd=repo_dir)
    run(["git", "add", "-A"], cwd=repo_dir)
    run(["git", "commit", "-m", title], cwd=repo_dir)
    run(["git", "push", "--force", "origin", branch], cwd=repo_dir)


def pr_body(work, body):
    """The reviewer-facing text, plus the hidden attempt counter."""
    attempt = work["attempt"]
    note = ""
    if attempt > 1:
        note = (f"\n\n_Attempt {attempt}. The previous attempt is replaced, not added "
                "to — read the diff as a whole._")
    return f"{body}{note}\n\n<!-- attempt: {attempt} -->"


def open_or_update_pr(work, title, body):
    repo = work["repo"]
    if work["pr_number"]:
        run(["gh", "pr", "edit", str(work["pr_number"]), "--repo", f"{OWNER}/{repo}",
             "--title", title, "--body", body])
        run(["gh", "pr", "edit", str(work["pr_number"]), "--repo", f"{OWNER}/{repo}",
             "--remove-label", TRY_AGAIN], check=False)
        return work["pr_number"]
    result = run(["gh", "pr", "create", "--repo", f"{OWNER}/{repo}", "--draft",
                  "--head", work["branch"], "--base", default_branch(repo),
                  "--title", title, "--body", body])
    return result.stdout.strip().rsplit("/", 1)[-1]


def publish(work):
    repo = work["repo"]
    repo_dir = Path("work") / repo
    out = Path(f"build/out/{repo}.md")
    note = Path(f"build/notes/{repo}.md")

    if not out.exists():
        if note.exists():
            hand_back(work, note.read_text().strip())
        else:
            hand_back(work, "The build run ended without producing a change or an "
                            "explanation. Nothing was written to this project. The run "
                            "log has the detail.")
        return

    title, body = split_title(out.read_text())
    if not title:
        hand_back(work, "The build finished but did not name the change, so nothing "
                        "was opened. This is a fault in the factory, not in the task — "
                        "re-approving it is safe.")
        return

    if not tree_changed(repo_dir):
        hand_back(work, f"The build finished without changing any file, so there is "
                        f"nothing to review.\n\nWhat it reported:\n\n{title}")
        return

    commit_and_push(work, repo_dir, title)
    number = open_or_update_pr(work, title, pr_body(work, body))
    if work["issue_number"]:
        relabel(repo, work["issue_number"], add=[BUILT], remove=[BUILDING, APPROVED])
    print(f"- {repo}: draft PR #{number} — {title}")


def main():
    work = load_work()
    if not work:
        print("No work was selected this run. Nothing to publish.")
        return 0
    publish(work)
    return 0


if __name__ == "__main__":
    sys.exit(main())
