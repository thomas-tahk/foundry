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

### L1 promotes, it does not generate

L1 does not invent next steps. L0 has already written three per repo, and a second
loop generating its own list in parallel would produce two competing backlogs that
drift apart — the same duplication that comes from running three orchestration
frameworks side by side.

Instead, L1 **promotes** one of L0's next steps into a full proposal: it picks the
step, verifies the evidence still holds, and adds the done-gate, the blast radius, and
the implementation notes that L0 deliberately omits. One source of candidate work
(L0), one refiner (L1), one queue.

If L1 believes no L0 step is worth promoting, it writes nothing and says so in the run
log. If it believes L0 missed something, it proposes an *edit to the Resume issue*
rather than opening a competing proposal.

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

Every proposal carries a `Source:` line naming exactly where it came from — an L0
Resume step, an L3 check, or a named intent document. Before opening, a loop must
confirm that no open `factory:proposed`, no `factory:declined`, and no open PR already
covers that source. One source, one live proposal, ever.

Check the cap. If the cap is hit, write nothing — a silent run is the correct outcome
when the queue is full.

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

## Agent orchestration

A factory implies a head coordinating workers, not one agent doing everything in
sequence. It does here too — but pointed deliberately, because parallelism helps in
some places and actively hurts in others.

### The principle

**Parallelize investigation and verification. Serialize code generation.**

Parallel generation is the tempting version and the wrong one. Two agents editing the
same file overwrite each other, and more concurrent code production against a fixed
human review budget makes the bottleneck worse, not better. Parallel *investigation*
and parallel *review* do the opposite: they make each PR cheaper for a human to judge.
That is the direction worth spending tokens on.

### Where each pattern lives

| Loop | Pattern | Why |
|---|---|---|
| **L0 census** | Fan-out — one subagent per repo, lead assembles the results | Fifteen independent reads with no shared state. Textbook fan-out, and it makes the weekly sweep fast |
| **L1 promote** | Single agent | A judgment call over one queue. Parallelism adds cost and nothing else |
| **L2 build** | **Lead + phased fan-out.** See below | The real head-and-workers structure |
| **L3 keep-warm** | Fan-out — one subagent per repo per check | Independent mechanical checks |
| **Across approvals** | N approved issues run as N concurrent workflow runs | Job-level parallelism, free, already implied by the label trigger |

### Budget: a $20 Pro subscription is the binding constraint

The factory is built by someone on the $20 Pro plan: a 1× multiplier, a rolling
five-hour window, and a weekly cap, with Claude Code usage drawing on the same pool
as chat. That single fact drives every choice in this section.

**The factory runs on a metered API key, not the subscription token.** Authenticating
Actions with `CLAUDE_CODE_OAUTH_TOKEN` would make every overnight run compete with the
next day's interactive work for the scarcest resource available. A pay-as-you-go key
separates the budgets, makes factory spend independently visible, and gives it a hard
ceiling that cannot eat into the user's own capacity.

Estimated monthly cost at this scale — roughly **$12**, drawing nothing from Pro:

| Loop | Model | Rough monthly |
|---|---|---|
| L0 census, 15 repos weekly | Haiku 4.5 | ~$0.50 |
| L1 proposer, 3 repos, 3×/week | Sonnet 5 | ~$3.50 |
| L2 builder, ~8 PRs | Sonnet 5 | ~$7.00 |
| L3 keep-warm | mostly deterministic + Haiku | ~$0.50 |

**Deterministic first, model second.** Most of L0 and L3 needs no model at all: stranded
branches, CI status, dependency age, last-commit age, and unchecked boxes are all
mechanically derivable — the existing `generate_report.py` already proves the pattern.
Python gathers the facts; the model writes the narrative over facts already in hand. That
keeps prompts small and puts the token spend only where judgment actually happens.

**A model ladder, declared per loop.** `--model` in `claude_args` sets it per workflow:

| Loop | Model | Why |
|---|---|---|
| L0 narrative | Haiku 4.5 | Summarizing pre-gathered facts, not reasoning |
| L1 proposals | Sonnet 5 | Judgment about what is worth doing |
| L2 implementation | Sonnet 5 | Escalates to Opus 5 only on a `factory:deep` label |
| L3 checks | deterministic; Haiku for summaries | Mechanical |

### L2 in detail — lead and workers

**Agent count is a dial, not a constant.** The seven-context pipeline below is a
Max-plan shape; on Pro it would be unaffordable at any real volume. The profile is
declared per repo, and a `factory:deep` label promotes a single issue one level:

| Profile | Contexts | Shape |
|---|---|---|
| **`lean`** (default on Pro) | 2 | Lead + one implementer; the lead reviews the diff itself against the three lenses |
| `standard` | 4 | Lead + implementer + two verifiers (security, still-stubbed) |
| `full` | 7 | The complete pipeline below |

Start at `lean`. Promote a specific issue with `factory:deep` when it touches something
that genuinely warrants three reviewers; promote the whole repo only once the budget
proves it is affordable.

The session that receives the approved issue acts as lead. It never writes code itself.

1. **Investigate — 3 subagents in parallel.** One reads the intent documents and the
   issue's cited evidence. One maps the affected code and its call sites. One looks for
   prior art: existing tests, similar past PRs, relevant skills in the repo. Each
   reports back to the lead.
2. **Synthesize — lead only.** The lead reconciles the three reports into one plan and
   resolves contradictions between them. Disagreement between workers is signal, not
   noise: it usually marks the part a human should look at hardest.
3. **Implement — one agent, alone.** A single worker writes the code against the plan
   and runs the tests. One writer means no file conflicts and no overwrites.
4. **Verify — 3 subagents in parallel, on the diff.** A security lens, a test-coverage
   lens, and a "what is still mocked, stubbed, or hardcoded" lens. None of them may
   edit code; they report findings only.
5. **Report — lead only.** The lead writes the PR body: what changed, what the three
   verifiers found, and the mandatory still-stubbed section. Findings the lead
   dismisses are listed anyway, with the reason.

The human then reviews a PR that arrives pre-critiqued from three angles, with
disagreements surfaced rather than smoothed over. That is the point: not more PRs,
better-annotated ones.

### Model portability

The factory should survive a change of model or provider — a cheaper option, a local
one, or a different vendor entirely. One constraint shapes how:

**Claude Code cannot be pointed at a non-Claude model.** The official gateway
documentation states plainly that Anthropic "doesn't support routing Claude Code to
non-Claude models through any gateway." Ollama and vLLM now expose Anthropic-compatible
endpoints, so it may work in practice today — but it is unsupported and can break on any
release. Do not build on it.

So portability lives in the **assets**, not the runner:

1. **Prompts are committed files**, not inline YAML strings — `.factory/prompts/l0-census.md`
   and siblings. The workflow step reads a file; it does not embed the prompt.
2. **The runner step is thin.** Swapping `anthropics/claude-code-action` for an
   OpenCode, Aider, or Cline step is one YAML block per loop, against unchanged prompts.
3. **Every artifact is model-agnostic** — issues, labels, PRs, `LESSONS.md`, `repos.txt`.
   None of it encodes a vendor.

This is the second reason GitHub Actions beat cloud Routines: Routines store their
configuration in a web UI on one account, which is a lock-in the YAML approach avoids.

**Where a cheaper or local model actually fits.** Open-weight coding models sit in the
low 70s on SWE-bench Verified against the high-80s/mid-90s closed frontier — a gap that
matters for writing code and barely matters for summarizing facts already gathered.
So the seam is per loop, and it favours exactly the loops that run most often:

| Loop | Open-weight viability |
|---|---|
| L0 census, L3 checks | **Good fit** — narration over deterministic facts. The natural first experiment |
| L1 proposals | Marginal — judgment about what deserves building |
| L2 implementation | Poor today — this is where the benchmark gap bites, and where "tests green" has to actually hold |

### Subagents, not agent teams

Subagents each get their own context window and report to the lead. Agent teams add
direct teammate-to-teammate messaging and a shared task list — at significantly higher
token cost, with an experimental flag, no session resumption, and an explicit warning
against long unattended runs.

The factory's workers do not need to talk to each other; they need to report to a
lead. That is exactly the subagent model, so the factory uses subagents throughout.

The one case that would justify teams is adversarial debugging — several agents
holding competing hypotheses and actively trying to disprove each other, which beats
sequential investigation because it defeats anchoring. That is a future L4, opened only
when a real bug resists the normal loop, and never as an unattended cron job.

## The factory's brain

A GitHub Actions runner sees only what is committed to a repository. It cannot read
`~/.claude/CLAUDE.md`, the local memory directory, the globally-installed skills, or
`PLAYBOOK.md`. Everything the factory should know has to be made portable on purpose.
This section is what turns the loops from mechanical scripts into something that
actually uses what is available.

### 1. Portable context

Three committed files in the hub, passed to every loop:

| File | Holds | Read by |
|---|---|---|
| `CLAUDE.md` (hub root) | The factory's operating charter — evidence rule, done-gate discipline, no `Co-Authored-By`, surgical-change rule, verify-don't-guess rule | Every loop, automatically |
| `docs/factory/LESSONS.md` | What has and has not worked across these projects | L1, L3 before proposing |
| `docs/factory/PROJECTS.md` | Per-repo standing intent: what it is for, what "done" means, what is explicitly out of scope | L0, L1 |

`LESSONS.md` is seeded from history that already exists and is not otherwise
recoverable from git — for example: four projects were parked in a row after being
built on synthetic premises rather than real pull; the selection lesson was to
concentrate on work with intrinsic pull and checkable ground truth; a green unit test
is a weaker signal than an end-to-end reproduction. A proposal that contradicts a
recorded lesson must say so and argue the case, or not be opened.

Each target repo's own `CLAUDE.md` is read automatically after checkout, so per-repo
conventions need no special handling.

### 2. Skills

Repo-local `.claude/skills/` load after checkout and are available to L2. Plugin
skills are installed per-workflow through the action's `plugin_marketplaces` and
`plugins` inputs, and a loop's prompt may be a skill invocation rather than prose.
Where a repo already has skills configured — `knowflow` has the mattpocock engineering
skills wired up — the factory uses them rather than reinventing the workflow.

### 3. Research and current information

Runners have network access, so `WebSearch` and `WebFetch` are granted to L1 and L2
through `--allowedTools`. This exists to serve one specific rule, carried over from the
user's standing conventions:

> Never assume a library API method exists. Verify against official documentation, or
> stop and ask.

In factory terms: a proposal or implementation touching an unfamiliar or
version-sensitive library must cite the official documentation it verified against. If
it cannot reach the documentation, it applies `factory:blocked` and explains what it
needs — it does not guess. Research also covers checking whether a proposed approach
is still current before recommending it.

### 4. Skill supply chain

The factory does not have to be limited to skills that already exist locally. It may
find them, write them, and feed the good ones back to the workstation. Three paths,
each ending in a reviewed diff:

**Adopt.** When a loop hits a task someone has already solved well, it may research
public skill sources and *propose* one — as a PR editing the workflow's
`plugin_marketplaces` and `plugins` inputs, pinned to a specific marketplace and
version. The proposal must name the source, say what the skill does, and say why the
existing set is insufficient.

**Author.** When the factory finds itself doing the same multi-step workflow a third
time, it proposes a skill instead of repeating the steps. New skills land in the target
repo's `.claude/skills/`, where L2 picks them up automatically after checkout.

**Promote.** A skill that proves useful across more than one repo is proposed for the
hub's `skills/` directory. Merging it there makes it available to the workstation:
`~/.claude/` is already version-controlled through the `dotfiles` repo via symlinks, so
promotion is a documented local sync step the user runs, not something the cloud
reaches in and does. The cloud never writes to the workstation.

**The supply-chain rail:** a third-party skill is executable instruction, not data.
The factory may never install one during a run. Adoption always arrives as a PR diff
the user reads before merging, pinned to a version, from a named source. An unpinned
or unnamed source is an automatic `factory:blocked`.

### 5. Context budgets

The brain trickles into every loop, so it is the one part of this design that can rot
by accumulation. Three rules keep it bounded:

**Hard budgets, enforced in CI.** A workflow fails if any brain file exceeds its size:

| File | Budget |
|---|---|
| Hub `CLAUDE.md` | 100 lines |
| `LESSONS.md` | 30 entries, one line each plus a link |
| `PROJECTS.md` | 10 lines per repo |

**Eviction is a first-class operation.** When the learning loop wants to add a lesson
to a full file, it must consolidate two existing entries or evict one, and say which
and why. Append-only is how a brain becomes a swamp.

**Skills are opt-in per loop, never inherited.** Each workflow declares its own
`--allowedTools` and plugin list. L0 is read-only and gets no skills at all. L1 gets
research tools. L2 gets the target repo's own `.claude/skills/` after checkout. There
is no ambient global layer for a loop to accumulate into — which is the structural
reason a cloud factory cannot bloat the way a workstation does.

**Adoption is zero-sum.** A proposal to adopt a third-party skill must either name a
skill to retire or argue explicitly why nothing should go. Collections grow by default
because acquiring feels productive and pruning does not; making adoption cost something
is what keeps the set honest.

### 6. Learning loop

Static rules decay. Monthly, a run reads every `factory:declined` issue and every
closed-unmerged factory PR, looks for the pattern behind the rejections, and opens a
PR against `LESSONS.md` proposing what it learned. That PR is reviewed like any other —
the factory proposes what it learned; the user decides what it knows.

This is what makes the caps and the evidence rule improve over time instead of
calcifying.

### 7. The rails

"Use everything available" and "don't go off the rails" are the same design problem.
The rails are these, and none of them is negotiable by the factory itself:

- **Draft PRs only. No merges. No pushes to `main`.** The one irreversible step is human.
- **Evidence or silence.** No citation, no issue. A full queue means write nothing.
- **Escalate instead of guessing.** Uncertainty becomes `factory:blocked` with a
  specific question, never a plausible-looking assumption.
- **Bounded tools.** Each loop's `--allowedTools` grants only what that loop needs;
  L0 is read-only and cannot write code at all.
- **Bounded runs.** `--max-turns` and `timeout-minutes` on every job.
- **No self-modification.** The factory may propose changes to its own workflows,
  lessons, and skills through a normal reviewed PR. It may never edit them in place
  during a run, and it may never install a third-party skill mid-run.
- **Secrets never surface.** No secret is echoed, printed, or written to a log or an
  issue body, in any form, masked or otherwise.

## Authentication and secrets

| Secret | Where | What |
|---|---|---|
| `FACTORY_GH_TOKEN` | hub | Fine-grained PAT, selected repos: Issues RW, Contents R, Pull requests R, Actions R |
| `ANTHROPIC_API_KEY` | hub + each elected repo | Metered pay-as-you-go key. Keeps factory spend off the Pro subscription — see §Budget |

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
| Two loops generating competing backlogs | One generator (L0), one refiner (L1); mandatory `Source:` line; one live proposal per source |
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
| **0** | Portable brain: hub `CLAUDE.md`, `LESSONS.md`, `PROJECTS.md` | Nothing — but every later phase reads these, so they come first |
| **1** | L0 census, hub, all 15 repos; drop the `Stale:` section from `generate_report.py` | The Resume issue is genuinely worth reading. If it isn't, stop here — the rest rests on this |
| **2** | L1 proposer, `knowflow` only | Proposals grounded in real evidence are worth approving |
| **3** | L2 builder, `knowflow` only | The full loop closes: label on phone → draft PR by evening |
| **4** | L3 keep-warm; scale to `priority-post` and `pocket-draft` | It holds at three repos |

Phase 1 is also the pilot. It is read-only, so it can ship without risk to any repo.

## Open decisions

None. Every decision above is settled; the remaining unknowns are empirical and
answered by running Phase 1.
