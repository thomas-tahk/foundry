# Factory Phases 0 + 1 — Portable Brain and L0 Census

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the factory's committed brain (`CLAUDE.md`, `LESSONS.md`, `PROJECTS.md`, `elected.txt`) and the L0 census loop, so that every Monday each repo in `repos.txt` has one continuously-updated GitHub issue titled `▶ Resume here — <repo>` that tells the user where that project stands and what the three smallest next steps are.

**Architecture:** Deterministic-first, model-second, in three separated stages. A Python script gathers facts from the GitHub REST API and writes them to a JSON file. `claude-code-action` reads that JSON and writes one Markdown narrative per repo to disk — it is given **no credentials and no network-writing tools**. A second Python script upserts those Markdown bodies as GitHub issues. Splitting judgment from API calls makes both Python stages unit-testable, keeps the model's prompt small, and means a model failure can never half-write an issue.

**Tech Stack:** Python 3 standard library only (`urllib`, `json`, `unittest`) — matching `scripts/generate_report.py`, which has zero dependencies. GitHub Actions. `anthropics/claude-code-action@v1`.

## Global Constraints

- **Python: standard library only.** No `requests`, no `PyGithub`. `scripts/generate_report.py` establishes this pattern; follow it.
- **Prompts are committed files under `.factory/prompts/`, never inline YAML strings.** Spec §Model portability: "The workflow step reads a file; it does not embed the prompt."
- **The model stage gets no tokens.** `GITHUB_TOKEN` and `FACTORY_GH_TOKEN` are never present in the environment of the `claude-code-action` step.
- **Authentication is a metered API key**, `ANTHROPIC_API_KEY`. Spec §Budget: the OAuth token "would make every overnight run compete with the next day's interactive work."
- **Do not pass `github_token: ${{ secrets.GITHUB_TOKEN }}` to `claude-code-action`.** Spec §Known constraints #1.
- **Model ladder for L0 narrative: `claude-haiku-4-5-20251001`.** Spec §Budget: "Summarizing pre-gathered facts, not reasoning."
- **No `Co-Authored-By` trailers on any commit.**
- **Never print a secret**, masked or otherwise.
- Issue title format is exactly `▶ Resume here — <repo>` (U+25B6, then an em dash U+2014 with single spaces).
- Label applied to every census issue: `factory:resume`.

---

## File Structure

| Path | Responsibility |
|---|---|
| `CLAUDE.md` (exists, untracked) | The operating charter the factory carries into every run. Commit as-is. |
| `docs/factory/LESSONS.md` (exists, untracked) | 30-entry lesson budget, read before proposing. Commit as-is. |
| `docs/factory/PROJECTS.md` (new) | One entry per repo: what it is, where it stands, its done-gate. The context L1/L2 read to avoid re-deriving a project from scratch. |
| `elected.txt` (new) | Build tier — repos where the factory may propose and build. One name per line. |
| `scripts/census_facts.py` (new) | Stage 1. Pure fact-gathering over the GitHub REST API → `census/facts.json`. No judgment, no model. |
| `scripts/census_publish.py` (new) | Stage 3. Upserts `census/out/<repo>.md` as one labelled issue per repo. Idempotent: edits in place, never duplicates. |
| `tests/test_census_facts.py` (new) | Unit tests for Stage 1's pure functions over fixture payloads. |
| `tests/test_census_publish.py` (new) | Unit tests for Stage 3's upsert decision (create vs. edit) and body assembly. |
| `.factory/prompts/l0-census.md` (new) | Stage 2's prompt. Reads `census/facts.json`, writes `census/out/<repo>.md`. |
| `.github/workflows/factory-census.yml` (new) | Wires the three stages, Monday 06:00 UTC + `workflow_dispatch`. |
| `scripts/generate_report.py` (modify) | Remove the `Stale:` line — superseded by L0's per-repo "last commit N days ago". |

`census/` is a build artifact directory, not committed. Add it to `.gitignore`.

---

### Task 1: Commit the portable brain

**Files:**
- Commit: `CLAUDE.md`, `docs/factory/LESSONS.md` (both already written, currently untracked)
- Modify: `docs/superpowers/specs/2026-08-08-software-factory-design.md` (secrets table)

**Interfaces:**
- Consumes: nothing.
- Produces: `CLAUDE.md` and `docs/factory/LESSONS.md` tracked on the branch — every later task's workflows reference them by path.

- [ ] **Step 1: Verify the two files exist and are non-empty**

```bash
cd /Users/tnt/Projects/foundry
wc -l CLAUDE.md docs/factory/LESSONS.md
```

Expected: `CLAUDE.md` ~100 lines, `LESSONS.md` ~60 lines. If either is missing, stop — they were written in a prior session and must not be regenerated from scratch.

- [ ] **Step 2: Fix the spec's contradictory secrets table**

`docs/superpowers/specs/2026-08-08-software-factory-design.md` §Authentication and secrets lists `CLAUDE_CODE_OAUTH_TOKEN`, which §Budget explicitly rejects. Replace that table row:

```markdown
| `ANTHROPIC_API_KEY` | hub + each elected repo | Metered pay-as-you-go key. Keeps factory spend off the Pro subscription — see §Budget |
```

Leave the `FACTORY_GH_TOKEN` row unchanged.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md docs/factory/LESSONS.md docs/superpowers/specs/2026-08-08-software-factory-design.md
git commit -m "docs(factory): commit the portable brain; fix the auth table to the metered key"
```

---

### Task 2: Write `PROJECTS.md` and `elected.txt`

**Files:**
- Create: `docs/factory/PROJECTS.md`
- Create: `elected.txt`

**Interfaces:**
- Consumes: nothing.
- Produces: `elected.txt`, parsed by future L1/L2/L3 workflows with the same comment-and-blank-line rules `repos.txt` uses (`line.split("#", 1)[0].strip()`).

- [ ] **Step 1: Write `docs/factory/PROJECTS.md`**

One entry per repo currently in `repos.txt`. Each entry is exactly four lines — anything longer is a swamp, per the `LESSONS.md` budget rule. Write only what you can source from the repo itself or from `repos.txt`; if a project's done-gate is unknown, write `Done-gate: not yet stated` rather than inventing one.

```markdown
# Projects

What each tracked project is, where it stands, and the one transaction that proves it
works. Read this before proposing work in any repo. Budget: one four-line entry per
repo. This file is not append-only — when a project is retired, delete its entry.

Format:

    ## <repo>
    **Is:** <one line — what the thing is>
    **Stands:** <one line — the current state, with a citation: a branch, a path, a PR>
    **Done-gate:** <one user-observable transaction that proves it works>

---

## pocket-draft
**Is:** Pokémon TCG Pocket draft tool plus a Go rules engine that plays drafted decks.
**Stands:** `feat/draft-mode-flow` is 21 commits ahead of `main` and contains all of PR #1; the draft → deckbuild → play loop runs end to end locally, but the opponent still plays a hardcoded preset (`server/carddata.go:187-189`) and no card effects exist (`engine/types.go:64`).
**Done-gate:** I open the live site, draft a deck, play a run against a bot drafted from the same pool where cards do what their text says, and my run record persists.

## knowflow
**Is:** Service-desk tool turning KB text into editable, accessible preset diagrams.
**Stands:** Live on Vercel + Supabase, zero open PRs; code and flow content deploy on separate tracks — merging never updates flows, only `npm run seed:flows -- --force` does.
**Done-gate:** A teammate opens the live URL, reads an official flow without a password, and I edit one after unlocking.

## priority-post
**Is:** Personal smart to-do app with an AI planner.
**Stands:** Live on Vercel; `phase-3-discord-planner` is built and green but never merged, pending manual go-live wiring (Discord app, Vercel secret, Neon migration, Railway deploy).
**Done-gate:** I message the Discord bot, it plans my real tasks, and the plan appears in the live app.
```

Then add a four-line entry for every remaining repo in `repos.txt` (`TTunes`, `kb-helper`, `thomas-tahk-portfolio-game`, `llm-plays-sc`, `job-app-dispatch`, `shows-for-us`, `amugonna`, `ai-advisor`, `Dormant`, `ez-golf`, `pwp-rts-timeline`, `esports-tldr`). For any repo you cannot characterise from its README or `docs/`, write:

```markdown
## <repo>
**Is:** not yet characterised
**Stands:** no entry written yet — the first L0 census run will supply the evidence
**Done-gate:** not yet stated
```

That placeholder is deliberate and allowed: it is an honest statement of absence, not a TBD standing in for work this plan should have done.

- [ ] **Step 2: Write `elected.txt`**

```
# Build tier: repos where the factory may propose (L1), build (L2), and keep warm (L3).
# A strict subset of repos.txt. Same rules: one repo name per line, # starts a comment.
# Adding a line here is the election. Keep this list short — the binding constraint is
# review capacity, not agent throughput.

pocket-draft
```

- [ ] **Step 3: Commit**

```bash
git add docs/factory/PROJECTS.md elected.txt
git commit -m "docs(factory): project context file and the build-tier election list"
```

---

### Task 3: Stage 1 — census fact gathering

**Files:**
- Create: `scripts/census_facts.py`
- Test: `tests/test_census_facts.py`
- Modify: `.gitignore` (add `census/`)

**Interfaces:**
- Consumes: `repos.txt` via the same parsing rules as `generate_report.py`.
- Produces: `census/facts.json` — a JSON object `{"generated_at": "<ISO8601>", "repos": [RepoFacts, ...]}` where each `RepoFacts` is:

```python
{
  "repo": str,
  "default_branch": str | None,
  "days_since_last_commit": int | None,
  "last_commit": {"sha": str, "date": str, "subject": str} | None,
  "open_prs": [{"number": int, "title": str, "draft": bool, "head": str, "age_days": int}],
  "stranded_branches": [{"name": str, "ahead_by": int, "last_commit_date": str, "age_days": int}],
  "intent_docs": [str],       # repo-relative paths
  "test_command": str | None, # e.g. "go test ./...", "npm test"
}
```

`census_publish.py` and `.factory/prompts/l0-census.md` both read exactly these keys. Do not rename them.

- [ ] **Step 1: Write the failing test**

Create `tests/test_census_facts.py`:

```python
import unittest
from datetime import datetime, timezone

from scripts.census_facts import (
    age_in_days,
    detect_test_command,
    pick_intent_docs,
    stranded_branches,
)


class TestAgeInDays(unittest.TestCase):
    def test_counts_whole_days_between_iso_timestamps(self):
        # Arrange
        now = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        # Act
        result = age_in_days("2026-08-05T12:00:00Z", now)
        # Assert
        self.assertEqual(result, 7)

    def test_returns_none_for_missing_timestamp(self):
        now = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        self.assertIsNone(age_in_days("", now))


class TestDetectTestCommand(unittest.TestCase):
    def test_go_module_yields_go_test(self):
        self.assertEqual(detect_test_command(["go.mod", "main.go"], {}), "go test ./...")

    def test_package_json_test_script_yields_npm_test(self):
        files = ["package.json"]
        pkg = {"scripts": {"test": "vitest run"}}
        self.assertEqual(detect_test_command(files, pkg), "npm test")

    def test_package_json_without_test_script_yields_none(self):
        self.assertIsNone(detect_test_command(["package.json"], {"scripts": {"dev": "vite"}}))

    def test_no_recognised_manifest_yields_none(self):
        self.assertIsNone(detect_test_command(["README.md"], {}))


class TestPickIntentDocs(unittest.TestCase):
    def test_prefers_vision_and_spec_files_over_incidental_markdown(self):
        # Arrange
        paths = [
            "README.md",
            "docs/VISION.md",
            "docs/superpowers/specs/2026-07-12-draft-mode-full-flow-design.md",
            "node_modules/foo/README.md",
            "docs/adr/0001-go-rules-engine-on-server.md",
        ]
        # Act
        result = pick_intent_docs(paths)
        # Assert
        self.assertIn("README.md", result)
        self.assertIn("docs/VISION.md", result)
        self.assertIn("docs/superpowers/specs/2026-07-12-draft-mode-full-flow-design.md", result)
        self.assertNotIn("node_modules/foo/README.md", result)

    def test_caps_the_list_so_the_prompt_stays_small(self):
        paths = [f"docs/spec-{i}.md" for i in range(50)]
        self.assertLessEqual(len(pick_intent_docs(paths)), 12)


class TestStrandedBranches(unittest.TestCase):
    def test_branch_ahead_with_no_open_pr_is_stranded(self):
        # Arrange
        comparisons = {"feat/x": {"ahead_by": 9, "last_commit_date": "2026-07-14T20:49:32Z"}}
        now = datetime(2026, 8, 12, tzinfo=timezone.utc)
        # Act
        result = stranded_branches(comparisons, set(), now=now)
        # Assert
        self.assertEqual(result[0]["name"], "feat/x")
        self.assertEqual(result[0]["ahead_by"], 9)
        self.assertEqual(result[0]["age_days"], 29)

    def test_branch_with_an_open_pr_is_not_stranded(self):
        comparisons = {"feat/x": {"ahead_by": 9, "last_commit_date": "2026-07-14T20:49:32Z"}}
        now = datetime(2026, 8, 12, tzinfo=timezone.utc)
        self.assertEqual(stranded_branches(comparisons, {"feat/x"}, now=now), [])

    def test_branch_not_ahead_is_not_stranded(self):
        comparisons = {"feat/x": {"ahead_by": 0, "last_commit_date": "2026-07-14T20:49:32Z"}}
        now = datetime(2026, 8, 12, tzinfo=timezone.utc)
        self.assertEqual(stranded_branches(comparisons, set(), now=now), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /Users/tnt/Projects/foundry
python3 -m unittest discover -s tests -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.census_facts'`.

- [ ] **Step 3: Create the package marker so `scripts` is importable**

```bash
touch scripts/__init__.py tests/__init__.py
```

- [ ] **Step 4: Write the pure functions**

Create `scripts/census_facts.py`. Reuse `gh()` and `load_repos()` from `generate_report.py` by importing them — do not copy them:

```python
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
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
python3 -m unittest discover -s tests -v
```

Expected: 10 tests, all PASS.

- [ ] **Step 6: Add the API-calling `main()`**

Append to `scripts/census_facts.py`:

```python
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
```

- [ ] **Step 7: Run it for real against one repo and read the output**

```bash
cd /Users/tnt/Projects/foundry
printf 'pocket-draft\n' > /tmp/one-repo.txt
GITHUB_TOKEN=$(gh auth token) python3 -c "
import scripts.census_facts as c
from pathlib import Path
c.REPO_LIST_FILE = Path('/tmp/one-repo.txt')
import scripts.generate_report as g
g.REPO_LIST_FILE = Path('/tmp/one-repo.txt')
c.main()
"
python3 -m json.tool census/facts.json | head -60
```

Expected: `pocket-draft` shows `default_branch: "main"`, a `stranded_branches` entry for `feat/draft-mode-flow` with `ahead_by: 21`, one open PR (#1), and `test_command: "go test ./..."`.

**This step is the real gate on Stage 1.** If `stranded_branches` is empty or `ahead_by` is wrong, the facts are wrong and no amount of good narration will save the issue.

- [ ] **Step 8: Ignore the artifact directory and commit**

```bash
printf 'census/\n' >> .gitignore
git add scripts/__init__.py scripts/census_facts.py tests/__init__.py tests/test_census_facts.py .gitignore
git commit -m "feat(census): gather per-repo facts deterministically"
```

---

### Task 4: Stage 3 — publish the census issues

Stage 3 is written before Stage 2 deliberately: it defines the file contract the prompt must satisfy, and it can be tested without a model.

**Files:**
- Create: `scripts/census_publish.py`
- Test: `tests/test_census_publish.py`

**Interfaces:**
- Consumes: `census/out/<repo>.md` — one Markdown body per repo, written by Stage 2.
- Produces: one GitHub issue per repo titled `▶ Resume here — <repo>`, labelled `factory:resume`, edited in place on every subsequent run.

- [ ] **Step 1: Write the failing test**

Create `tests/test_census_publish.py`:

```python
import unittest

from scripts.census_publish import issue_title, pick_existing_issue


class TestIssueTitle(unittest.TestCase):
    def test_uses_the_exact_pinned_format(self):
        self.assertEqual(issue_title("pocket-draft"), "▶ Resume here — pocket-draft")


class TestPickExistingIssue(unittest.TestCase):
    def test_finds_the_open_issue_with_the_matching_title(self):
        # Arrange
        issues = [
            {"number": 4, "title": "Something else", "state": "open"},
            {"number": 7, "title": "▶ Resume here — pocket-draft", "state": "open"},
        ]
        # Act
        result = pick_existing_issue(issues, "pocket-draft")
        # Assert
        self.assertEqual(result, 7)

    def test_reopens_a_closed_resume_issue_rather_than_creating_a_second(self):
        issues = [{"number": 7, "title": "▶ Resume here — pocket-draft", "state": "closed"}]
        self.assertEqual(pick_existing_issue(issues, "pocket-draft"), 7)

    def test_returns_none_when_no_resume_issue_exists(self):
        issues = [{"number": 4, "title": "Something else", "state": "open"}]
        self.assertIsNone(pick_existing_issue(issues, "pocket-draft"))

    def test_does_not_match_another_repos_resume_issue(self):
        issues = [{"number": 7, "title": "▶ Resume here — knowflow", "state": "open"}]
        self.assertIsNone(pick_existing_issue(issues, "pocket-draft"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
python3 -m unittest discover -s tests -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.census_publish'`.

- [ ] **Step 3: Write the implementation**

Create `scripts/census_publish.py`:

```python
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
    """The number of this repo's Resume issue, open or closed, or None."""
    title = issue_title(repo)
    for issue in issues:
        if issue.get("title") == title:
            return issue["number"]
    return None


def run(args, **kwargs):
    """Run a gh command, raising on failure so the workflow fails loudly."""
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs)


def existing_issues(repo):
    result = run(["gh", "issue", "list", "--repo", f"{OWNER}/{repo}",
                  "--state", "all", "--label", LABEL, "--limit", "50",
                  "--json", "number,title,state"])
    return json.loads(result.stdout or "[]")


def ensure_label(repo):
    """Create the label if absent; a repeat run is a harmless no-op."""
    subprocess.run(["gh", "label", "create", LABEL, "--repo", f"{OWNER}/{repo}",
                    "--color", "1D76DB", "--description",
                    "The single pinned Resume issue, rewritten weekly by L0"],
                   text=True, capture_output=True)


def publish(repo, body):
    ensure_label(repo)
    number = pick_existing_issue(existing_issues(repo), repo)
    if number is None:
        run(["gh", "issue", "create", "--repo", f"{OWNER}/{repo}",
             "--title", issue_title(repo), "--label", LABEL, "--body", body])
        print(f"- {repo}: created")
        return
    run(["gh", "issue", "edit", str(number), "--repo", f"{OWNER}/{repo}", "--body", body])
    run(["gh", "issue", "reopen", str(number), "--repo", f"{OWNER}/{repo}"])
    print(f"- {repo}: updated #{number}")


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
```

Note on `gh issue reopen`: it exits non-zero on an already-open issue in some `gh` versions. If Step 5 surfaces that, wrap it in `subprocess.run(..., check=False)` — reopening is best-effort, not load-bearing.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python3 -m unittest discover -s tests -v
```

Expected: 15 tests, all PASS.

- [ ] **Step 5: Prove it end to end against a real repo**

```bash
mkdir -p census/out
printf '## State\n\nSmoke test of the census publisher. This body is at least one hundred characters long so the length guard does not skip it.\n' > census/out/pocket-draft.md
printf 'pocket-draft\n' > /tmp/one-repo.txt
python3 -c "
from pathlib import Path
import scripts.generate_report as g; g.REPO_LIST_FILE = Path('/tmp/one-repo.txt')
import scripts.census_publish as p; p.main()
"
gh issue list --repo thomas-tahk/pocket-draft --label factory:resume
```

Expected: one issue created. Run the same command a second time and confirm the output says `updated #N` and `gh issue list` still shows exactly **one** issue — that is the idempotence proof, and the reason this script exists as its own stage.

- [ ] **Step 6: Commit**

```bash
git add scripts/census_publish.py tests/test_census_publish.py
git commit -m "feat(census): upsert one Resume issue per repo, idempotent by title"
```

---

### Task 5: Stage 2 — the census prompt

**Files:**
- Create: `.factory/prompts/l0-census.md`

**Interfaces:**
- Consumes: `census/facts.json` (Task 3's schema).
- Produces: `census/out/<repo>.md` for every repo in the facts file (Task 4's contract).

- [ ] **Step 1: Write the prompt file**

Create `.factory/prompts/l0-census.md`:

```markdown
You are L0, the census loop of a personal software factory. Read
`docs/factory/CLAUDE.md`-equivalent rails in `CLAUDE.md` and the recorded lessons in
`docs/factory/LESSONS.md` before writing anything.

## Input

`census/facts.json` holds mechanically-gathered facts for every tracked repo:
default branch, days since last commit, last commit, open PRs, stranded branches
(ahead of default with no open PR), intent-document paths, and the test command.

`docs/factory/PROJECTS.md` holds a four-line entry per repo: what it is, where it
stands, and its done-gate. Where an entry says "not yet characterised", say so in
your output rather than inventing a characterisation.

## Task

For each repo in `census/facts.json`, write `census/out/<repo>.md` — the body of that
repo's Resume issue. Do not create issues; a later step publishes these files.

## Required structure

    ## State
    <2-4 sentences: what this project is and where the code stands. Every claim cites
    a path, a branch, or a commit from the facts file or PROJECTS.md.>

    ## Half-done work
    <Stranded branches with their ahead-by count and age; draft PRs; open PRs older
    than 14 days. One line each, with the branch or PR number. "None" if none.>

    ## Likely reason it stalled
    <One or two sentences, explicitly labelled as inference — begin with "Likely" or
    "Probably" — and naming the evidence it rests on. Omit this section entirely for a
    repo with a commit in the last 7 days.>

    ## Three smallest next steps
    1. <Independently startable in one sitting. Names a file or command.>
    2. <...>
    3. <...>

    ## Blockers
    <What would have to be true first. "None known" if none.>

    ## Facts
    - Last commit: <N> days ago (<sha> <subject>)
    - Tests: <test command, or "none detected">

## Rules

- **Evidence or silence.** Every claim in State and Half-done work cites something in
  the facts file. If you cannot cite it, do not write it.
- **Label inference.** "Likely stalled because…" is fine. Stating an inference as an
  observation is not.
- **No nagging.** The days-since-last-commit line is a neutral fact. Never add urgency,
  encouragement, or an exhortation to get back to work.
- **Never invent a next step you cannot ground.** If the facts do not support three
  steps, write the ones you can and say plainly that the rest need a look at the code.
- Write for someone reading on a phone in under a minute. Lead with the outcome.
  Fragments over sentences. No preamble.
- Write only to `census/out/`. Touch no other path.
```

- [ ] **Step 2: Verify the prompt against real facts before wiring any workflow**

```bash
cd /Users/tnt/Projects/foundry
mkdir -p census/out
claude -p "$(cat .factory/prompts/l0-census.md)" --model claude-haiku-4-5-20251001
cat census/out/pocket-draft.md
```

Expected: a body following the structure above, whose Half-done work section names `feat/draft-mode-flow` (21 ahead) and PR #1.

**This is the Phase 1 gate.** Read the output as the user would. If it is not worth acting on, stop and revise the prompt before building the workflow — per the spec, "If it isn't, stop here — the rest rests on this."

- [ ] **Step 3: Commit**

```bash
git add .factory/prompts/l0-census.md
git commit -m "feat(census): the L0 narrative prompt, as a committed file"
```

---

### Task 6: Wire the workflow

**Files:**
- Create: `.github/workflows/factory-census.yml`
- Modify: `scripts/generate_report.py:106,134-137` (drop the `Stale:` line)

**Interfaces:**
- Consumes: `ANTHROPIC_API_KEY` and `FACTORY_GH_TOKEN` repository secrets.
- Produces: nothing later tasks import.

- [ ] **Step 1: Remove the superseded `Stale:` section**

In `scripts/generate_report.py`, delete the `stale` assignment at line 106 and the two `out.append` lines that emit `**Stale (no commits this week):**` (lines 134-137, keeping the `## Flags` header and the "Open items" line).

- [ ] **Step 2: Run the report to confirm it still works**

```bash
GITHUB_TOKEN=$(gh auth token) python3 scripts/generate_report.py
grep -c "Stale" reports/*.md || echo "no Stale section — correct"
```

Expected: the script completes and the newest report has no `Stale` line.

- [ ] **Step 3: Write the workflow**

Create `.github/workflows/factory-census.yml`:

```yaml
name: Factory L0 — Census

on:
  schedule:
    # 06:00 UTC Monday, one hour after the weekly report.
    - cron: "0 6 * * 1"
  workflow_dispatch: {}

permissions:
  contents: read

concurrency:
  group: factory-census
  cancel-in-progress: false

jobs:
  census:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      # Stage 1 — deterministic facts. No model, no judgment.
      - name: Gather facts
        env:
          GITHUB_TOKEN: ${{ secrets.FACTORY_GH_TOKEN }}
        run: python3 -m scripts.census_facts

      # Stage 2 — narrative only. Deliberately given no token: this step must not
      # be able to reach the GitHub API, so a bad run cannot half-write an issue.
      - name: Write narratives
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Follow the instructions in .factory/prompts/l0-census.md exactly.
          claude_args: |
            --max-turns 40
            --model claude-haiku-4-5-20251001
            --allowedTools Read,Write,Glob,Grep

      # Stage 3 — publish. Fails loudly if Stage 2 wrote nothing.
      - name: Publish Resume issues
        env:
          GH_TOKEN: ${{ secrets.FACTORY_GH_TOKEN }}
        run: python3 -m scripts.census_publish
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/factory-census.yml scripts/generate_report.py
git commit -m "feat(census): weekly L0 workflow; drop the report's superseded Stale list"
```

- [ ] **Step 5: Hand off the secrets the user must create**

These cannot be done by an agent. Present them as a checklist:

1. Create a metered Anthropic API key at console.anthropic.com, set a monthly spend limit (~$25 covers the spec's ~$12 estimate with headroom), and add it as the `ANTHROPIC_API_KEY` secret on `thomas-tahk/foundry`.
2. Create a fine-grained GitHub PAT with **Issues: Read and write**, **Contents: Read**, **Pull requests: Read**, **Metadata: Read**, scoped to the repos in `repos.txt`; add it as `FACTORY_GH_TOKEN` on `thomas-tahk/foundry`.
3. Neither value is ever echoed, logged, or pasted into an issue.

- [ ] **Step 6: Fire it once by hand and read the result**

```bash
gh workflow run "Factory L0 — Census" --repo thomas-tahk/foundry
gh run watch --repo thomas-tahk/foundry
gh issue view --repo thomas-tahk/pocket-draft --web
```

**Phase 1 is done when** the `▶ Resume here — pocket-draft` issue exists, its Half-done work section names `feat/draft-mode-flow` with its real ahead-by count, and the user reads it and says it is worth acting on. If it is not, the answer is to revise `.factory/prompts/l0-census.md` — not to proceed to Phase 2.

---

## Phases 2–4 — deferred, deliberately

L1 (proposer), L2 (builder), and L3 (keep-warm) each get their own plan, written **after**
the Phase 1 gate passes. The spec is explicit that Phase 1 is the pilot and that the rest
rests on it; writing TDD-granular steps for three unbuilt loops against an unproven census
would be speculation.

What is already settled for those plans, so nothing is lost:

- **L2 lives in `pocket-draft`**, not the hub, because it checks out code and runs tests.
  It fires on `issues.labeled` with `factory:approved`, never on cron.
- **`pocket-draft` needs a `CLAUDE.md` before L2 runs.** It has none today; the builder
  would work without knowing the repo's conventions, its two Go modules, or that there is
  no JS test runner. Write it as the first task of the L2 plan.
- **The six `factory:*` labels** (`resume`, `proposed`, `approved`, `building`, `declined`,
  `blocked`) must exist in each elected repo. `census_publish.ensure_label` already
  demonstrates the idempotent creation pattern to reuse.
- **The done-gate for Phase 3** is the whole factory's gate: approve a proposal on a phone
  in the morning, read a draft PR with green tests that evening.
