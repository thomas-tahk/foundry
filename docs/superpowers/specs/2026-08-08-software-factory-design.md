# Foundry — a personal software factory

**Date:** 2026-08-08
**Repo:** `thomas-tahk/foundry` (renamed from `weekly-reports`)
**Status:** design approved, not yet built

## Problem

Thirty repos with GitHub remotes. Two are actively worked. Thirteen are flagged stale
every week. The stated cause is not lack of time — it is lost momentum, switched focus,
and getting stuck. A repo goes cold, and re-entering it costs more than the next step
is worth, so it stays cold.

Three jobs follow from that, and the factory does all three:

1. **Cut the cold-start cost** of re-entering a repo left cold.
2. **Produce reviewable work** — proposals and PRs queued for approval.
3. **Keep warm repos warm** — stop friction from accumulating in the first place.

## Goals

- Minimal input: approving work should cost a label tap on a phone.
- Runs unattended — overnight, during the workday, while occupied.
- Every unit of output is reviewable on both phone and desktop with no custom UI.
- Nothing irreversible happens without a human.

## Non-goals

- **No custom dashboard.** GitHub Issues and PRs already render on mobile and desktop,
  already notify, already sync. Building a UI here is pure maintenance debt.
- **No auto-merge.** Ever. See "The gate" below.
- **No resurrection of repos the user has genuinely stopped caring about.** The factory
  makes re-entry cheap for every repo but only *builds* where the user has elected it.
- **No second reporting system.** The existing deterministic weekly report stays.

## The gate

The single load-bearing constraint: **agent throughput is not the bottleneck, review
capacity is.** Agent-generated code inflates the PR queue while human approval stays
the pre-merge gate. A factory that produces eight PRs against a two-PR review budget is
net negative — it converts a momentum problem into a backlog problem.

Every cap in this design exists to keep output under the review budget:

| Cap | Value | Why |
|---|---|---|
| Open `factory:proposed` per repo | 2 | A third proposal means the first two aren't being read |
| L2 concurrency | 1 per issue | Relabeling can't double-fire a build |
| PRs opened by L2 | Only on explicit approval | Approval rate *is* the throughput governor |
| `--max-turns` / job timeout | Set per loop | Bounds cost of a run that goes sideways |

## Architecture

One hub repo drives three of the four loops. The fourth lives in each elected repo,
because it needs to check out code and run tests.

```
foundry (hub, public)
├── repos.txt          ← census tier: every repo the factory watches
├── elected.txt        ← build tier: repos where the factory may propose and build
├── scripts/
│   └── generate_report.py     (existing, unchanged)
└── .github/workflows/
    ├── weekly-report.yml      (existing, unchanged except the Stale section)
    ├── factory-census.yml     → L0
    ├── factory-propose.yml    → L1
    └── factory-keepwarm.yml   → L3

<each elected repo>
└── .github/workflows/
    └── factory-build.yml      → L2
```

### Enrollment

Two plain-text files, editable from GitHub's web UI, no code change to add a repo —
the pattern `repos.txt` already uses.

- `repos.txt` — census tier. Gets the weekly report and an L0 Resume issue.
- `elected.txt` — build tier, a subset. Additionally gets L1 proposals, L2 builds,
  and L3 keep-warm checks.

A repo enters the build tier by the user adding one line. That is the election.

### Label vocabulary

| Label | Applied by | Meaning |
|---|---|---|
| `factory:resume` | L0 | Marks the single pinned Resume issue. L0 rewrites it in place |
| `factory:proposed` | L1, L3 | Proposed work awaiting a decision |
| `factory:approved` | **User** | Triggers L2 in that repo |
| `factory:building` | L2 | In flight. Prevents double-fire |
| `factory:declined` | **User** | Never propose this again |
| `factory:blocked` | L1, L2, L3 | Needs something only the user can supply |

`factory:declined` is not cosmetic. Without a durable record of rejection, L1
re-proposes the same rejected work every run, and the queue becomes noise.

---

## L0 — Census

**Fires:** weekly cron, Monday 06:00 UTC (one hour after the existing report).
**Scope:** every repo in `repos.txt`.
**Writes:** exactly one issue per repo, edited in place, never duplicated.

For each repo, read: default-branch state, recent commits, open PRs, non-merged
branches, intent documents (`README`, `docs/`, spec and vision files), and test
configuration. Then upsert an issue titled `▶ Resume here — <repo>` with:

- **State** — what this project is and where the code currently stands
- **Half-done work** — stranded branches, draft PRs, unchecked roadmap boxes
- **Likely reason it stalled** — inferred from the evidence, stated as inference
- **Three smallest next steps** — each independently startable in one sitting
- **Blockers** — what would have to be true first
- **Last commit N days ago** — a neutral fact, no notification, no nagging

This is the loop that treats the actual stated problem. It is read-only, so it can
safely cover all fifteen repos while building covers three.

### Relationship to the existing weekly report

They do different jobs and both stay:

| Weekly report (Python, deterministic, free) | L0 Resume issue (LLM) |
|---|---|
| Rear-view: what happened last week | Forward: where you were, what's next |
| One document, all repos | One issue per repo, kept current |
| Commit lists and PR titles | Interpretation, next steps, blockers |

The one overlap is staleness. L0's "last commit N days ago" line supersedes the
report's crude `Stale:` list, so that section is removed from `generate_report.py`.
Nothing else in the report changes.

---

## L1 — Proposer

**Fires:** cron, three times weekly (Tue/Thu/Sat 06:00 UTC).
**Scope:** `elected.txt` only.
**Writes:** issues labeled `factory:proposed`, capped at 2 open per repo.

### The evidence rule

**Every proposal must cite a path, line, commit, or PR number. No citation, no issue.**

This is the most important rule in the document. Four projects have already been
parked after being built on invented premises rather than real pull. An agent
permitted to propose work from vibes will generate exactly that failure at machine
speed. The citation requirement forces every proposal to trace back to something the
user already wrote or something the repo already demonstrates.

Evidence sources, in precedence order:

1. **Intent documents the user wrote** — e.g. `knowflow/docs/superpowers/specs/
   2026-07-19-backend-persistence-and-ai-provenance-course.md`, `pocket-draft/docs/
   VISION.md`. Strongest source: these are the user's own stated intentions.
2. **Stranded work** — unmerged branches, draft PRs, `TODO` / `FIXME` comments
3. **Broken signal** — failing tests, skipped tests, red CI
4. **Unchecked boxes** in roadmaps and checklists

### Proposal format

- **What** — one sentence
- **Why now** — the citation
- **Done-gate** — one sentence naming a single user-observable transaction that
  proves it works. Not "tests pass"
- **Blast radius** — files likely touched, and whether it touches anything live

### Before opening

Check that no open `factory:proposed` issue and no `factory:declined` issue already
covers this. Check the cap. If the cap is hit, write nothing — a silent run is the
correct outcome when the queue is full.

---

## L2 — Builder

**Fires:** `issues.labeled` where the label is `factory:approved`. **Not cron.**
**Scope:** the repo the issue lives in.
**Writes:** a `claude/issue-<n>-<slug>` branch and a **draft** PR.

The event trigger is deliberate. Approving on a phone at 10:00 means the PR is waiting
by lunch, so workday gaps become the factory's clock. There is no idle burn, no queue
staleness, and throughput scales with approvals rather than with wall-clock time.

**Steps:** check out, implement against the issue, run the repo's test command, open a
draft PR linking the issue.

**The PR body must include a "Still mocked, stubbed, or hardcoded" section** listing
everything on the path the done-gate describes that is not real. If nothing is stubbed,
it says so explicitly. This section is not optional and not decorative — when an agent
reports success, this is the first thing worth reading.

**Guardrails:**

- Draft PRs only. Never pushes to `main`. Never merges.
- If tests fail, the job fails loudly and the PR is not opened. A green workflow badge
  must never imply a task succeeded when it did not.
- Concurrency group keyed on the issue number, so re-labeling cannot double-fire.
- Commits carry **no** `Co-Authored-By` trailer, per the user's git convention.
- `--max-turns` and `timeout-minutes` set, to bound a run that goes sideways.

### Merge stays human

The user reviews and taps Merge. On GitHub mobile that is one tap. Automating it would
save one tap and remove the only real gate in the system — a bad trade, and worse given
`knowflow` runs in production for the user's team.

---

## L3 — Keep-warm

**Fires:** weekly cron, Wednesday 06:00 UTC.
**Scope:** `elected.txt` only.
**Writes:** `factory:proposed` issues, under the same evidence rule as L1 and sharing
its cap — 2 open proposals per repo across L1 and L3 combined, not 2 each.

Repos go cold when friction accumulates: CI goes red, dependencies rot, a branch
strands, the next step gets fuzzy. L3 keeps friction near zero so re-entry stays cheap.
It checks:

- CI status on the default branch
- Dependency freshness
- **Stranded branches** — ahead of `main`, no open PR, no commits in 21 days
- Failing or skipped tests

Stranded branches are the highest-value check, because that pattern is the user's
dormancy mechanism made visible in git. Three exist right now:
`priority-post/phase-3-discord-planner` (built, green, never merged),
`pocket-draft/feat/draft-mode-flow`, `helpdesk-qol/slice-0-incident-view`.

---

## Authentication and secrets

| Secret | Where | What |
|---|---|---|
| `FACTORY_GH_TOKEN` | hub | Fine-grained PAT, selected repos: Issues RW, Contents R, Pull requests R, Actions R |
| `CLAUDE_CODE_OAUTH_TOKEN` | hub + each elected repo | From `claude setup-token`. Bills to the Max subscription, not the API |

The hub's default `GITHUB_TOKEN` is scoped to the hub repo alone and **cannot** open
issues in other repositories. That constraint is why the PAT exists. Elected repos'
L2 workflows use their own `GITHUB_TOKEN` and need no PAT.

Both secrets are GitHub Actions secrets. Neither is ever echoed, printed, or logged.

---

## Known constraints

Verified against current official documentation:

1. **Do not pass `github_token: ${{ secrets.GITHUB_TOKEN }}` to `claude-code-action`.**
   GitHub does not trigger workflows on commits made with the default token, so CI
   would never run on the agent's commits — and the "tests green" claim would be
   vacuous. Omit it so the action authenticates as the Claude GitHub App.
2. **Public repos disable scheduled workflows after 60 days without repository
   activity.** The hub commits a report weekly, so it stays alive. L2 is
   event-driven and unaffected.
3. **`claude-code-action` rejects bot actors** unless listed in `allowed_bots`. L2's
   triggering actor is the user adding a label — a human with write access, so this
   passes. Do not add automation that auto-applies `factory:approved`; it would both
   trip this check and remove the gate.
4. **A green run status does not mean the task succeeded.** Every loop needs its own
   success signal, checked in the artifact rather than in the badge.
5. All four repos involved are public, so Actions minutes are free. Cost is
   subscription usage only.

## Failure modes

| Failure | Mitigation |
|---|---|
| Proposal slop — plausible work nobody wants | Evidence rule; 2-per-repo cap; `factory:declined` is read before proposing |
| Review backlog exceeds capacity | Caps above; L2 only on approval |
| Silent failure — loops stop, nobody notices | Jobs fail loudly; the weekly report gains a factory-health line |
| Runaway cost | `--max-turns`, `timeout-minutes`, concurrency groups |
| Bad merge into a live product | Draft PRs only; merge is always human |
| Re-proposing rejected work | `factory:declined` label checked every run |
| Nagging | The going-cold marker is a neutral line in an issue, never a notification |

## Done-gate

> On a weekday morning I open GitHub on my phone, read a `factory:proposed` issue in
> one of my repos, judge it worth doing, add `factory:approved`, and by that evening a
> draft PR exists whose tests are green and whose "still stubbed" section is accurate.

Not "the workflows run." Not "the YAML is merged." That exact transaction.

## Build order

Each phase is independently useful and independently abandonable.

| Phase | Build | Proves |
|---|---|---|
| **1** | L0 census, hub, all 15 repos; drop the `Stale:` section from `generate_report.py` | The Resume issue is genuinely worth reading. If it isn't, stop here — the rest rests on this |
| **2** | L1 proposer, `knowflow` only | Proposals grounded in real evidence are worth approving |
| **3** | L2 builder, `knowflow` only | The full loop closes: label on phone → draft PR by evening |
| **4** | L3 keep-warm; scale to `priority-post` and `pocket-draft` | It holds at three repos |

Phase 1 is also the pilot. It is read-only, so it can ship without risk to any repo.

## Open decisions

None. Every decision above is settled; the remaining unknowns are empirical and
answered by running Phase 1.
