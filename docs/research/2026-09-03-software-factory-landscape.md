# Software-factory landscape — what actually ships, and what foundry should take from it

Research date: 2026-09-03. Every claim below traces to a page I fetched; anything I
could not fetch is marked **unverified**. Where a vendor's own pages contradict each
other, I say so.

---

## 1. Bottom line

No. There is nothing to adopt wholesale, because nobody sells what foundry is for.

Every working product is **task-first**: a human already knows what they want done and
hands it over — by assigning an issue, tagging a bot, or typing in Slack. Not one of
them sweeps a portfolio of dormant repos and tells you where to re-enter. That census
job is foundry's actual differentiator, and it is rarer than the user probably thinks.

The closest thing to foundry-as-a-framework is **GitHub Agentic Workflows (`gh-aw`)** —
markdown workflows in GitHub Actions, cron + event triggers, engine-agnostic, with a
cross-repo "safe outputs" layer that is a more mature version of foundry's Python
publisher. Its companion repo `githubnext/agentics` ships `Daily Repo Status`,
`Daily Plan`, `Repo Assist` and `CI Doctor` — recognisably L0, L1 and L3. It is worth
reading as a spec, not migrating to.

The two mechanisms worth lifting almost verbatim are **Claude's auto-fix pull requests**
(webhook-driven revise loop, per-PR toggle, escalates when ambiguous) and **Devin's
bot-comment allowlist** (the thing that stops a revise loop eating itself).

The uncomfortable finding: **L2 is the part of foundry with the worst
build-cost-to-uniqueness ratio.** It has never run, it costs the most per repo to
onboard, and four GA products do it better and cheaper — Jules does it free. Section 7
argues foundry should keep L0/L1/L3 and seriously consider outsourcing L2.

---

## 2. The landscape

Only systems I could verify as real and shipping. Dropped or demoted: Copilot Workspace
(status **unverified** — no sunset notice found, and it does not appear anywhere in the
current Copilot agent docs, which have been reorganised around "cloud agent"); Sweep (not
investigated); Kiro and Bugbot (secondary sources only); SWE-agent (superseded by
`mini-swe-agent`, a research/CLI tool, not a factory); Aider (local, human-in-the-loop,
included only for its trigger idea).

### 2a. Trigger, intake, scoping, plan gate

| System | 1. Trigger surface | 2. Intake (async / phone) | 3. Task scoping | 4. Plan/approval gate |
|---|---|---|---|---|
| **GitHub Copilot cloud agent** | Issue assignment (primary), agents panel/tab, dashboard Task button, `@copilot` on a PR | Assign an issue to Copilot from the GitHub mobile web UI; agents panel | 59-min hard execution cap per session | No built-in gate; docs *recommend* using it to research + plan on a branch before asking for a PR |
| **Devin (Cognition)** | Slack `@Devin`, web, GitHub `@`-mention, Linear/Jira, API, **Automations** (Slack / GitHub / Linear / schedule / webhook), scheduled sessions | Slack mention in a channel or DM — this is the flagship intake path | Explicit rule: "if a task would take you three hours or less, Devin can most likely do it"; ACU budget cap per session | No mandatory gate; guidance is to split into verifiable sub-tasks with checkpoints |
| **OpenAI Codex (cloud)** | Web (chatgpt.com/codex), ChatGPT mobile, Slack, GitHub, GitLab, Linear, CLI | Slack + ChatGPT mobile app | Parallel cloud tasks; per-plan concurrency (unverified numbers) | No gate; `/review` is a separate explicit command |
| **Claude Code Action** (`anthropics/claude-code-action@v1`) | `@claude` in issue/PR comment or PR review (interactive mode); any GitHub event incl. `schedule` when a `prompt` input is set (automation mode) | Comment `@claude` from GitHub mobile | `--max-turns`, workflow `timeout-minutes`, GH concurrency controls | None built in |
| **Claude routines** (`/schedule`, research preview) | Schedule (min interval 1 hour), API `POST /fire` with bearer token, GitHub events (`pull_request.*`, `release.*`) with field filters | `/schedule` from CLI; API endpoint from any phone-reachable tool; runs viewable in the Claude mobile app | Runs as a full autonomous cloud session, no permission prompts; daily per-account run cap | None — routines run unattended by design |
| **Claude Code on the web / mobile** | Browser at claude.ai/code, Claude mobile app, `claude --cloud "..."` from CLI | **Strongest phone story of anything surveyed**: start, monitor, steer and PR from the mobile app | Session-based; auto-compaction; `--cloud` per repo | Documented pattern: plan locally in `--permission-mode plan`, commit the plan, then `claude --cloud "Execute the migration plan in docs/…"` |
| **Google Jules** | Web app, Jules Tools CLI, REST API, scheduled tasks, GitHub | Web/mobile browser | 15 / 100 / 300 tasks per day by tier | **Yes — explicit.** "Jules will generate a plan. You can review and approve it before any code changes are made." Plus a **Planning Critic**: a secondary agent that reviews auto-approved plans, credited with a 9.5% failure-rate reduction (Jan 2026) |
| **Cursor cloud agents** | Cursor Web, Cursor for iOS, Desktop, **Slack `@Cursor`**, GitHub/Bitbucket comments, Linear, API | Slack and iOS app | Parallel agents, isolated VMs | None documented |
| **Factory.ai (Droids)** | Factory App, Droid CLI, `droid exec` headless, web/mobile, IDE, Automations (schedule / Slack / GitHub events, configured in the web UI) | Slack automation trigger; mobile surface | `droid exec --auto off\|low\|medium\|high`, fail-fast on permission violation | **Yes — two of them.** *Spec Mode* proposes a plan you approve before code. *Missions* (~1–500 features) require plan approval, then decompose into milestones run by worker agents under "Mission Control" |
| **OpenHands (OSS + Cloud)** | `openhands` **label on an issue**, `@openhands` mention on an issue or PR comment, web, CLI, API | Apply a label from the GitHub mobile app | Per-conversation; unlimited daily conversations on the free Individual tier | None documented |
| **gh-aw (GitHub Agentic Workflows)** | Any GH Actions event, `schedule` (incl. fuzzy "daily on weekdays"), `workflow_dispatch`, **`slash_command`**, **`label_command`** | `label_command` / `slash_command` from GitHub mobile | `stop-after` on triggers, per-safe-output `max:` caps | Not a gate, but the write phase is a separate job that can require a GH Actions `environment` (i.e. a manual approval) |
| **Ona (ex-Gitpod, "Part of OpenAI")** | Web, phone/tablet, source control + issue tracker integrations | "Fire off a task when you leave the office" — explicitly a phone pitch | Parallel agents in ephemeral environments | Unverified |
| **Aider** | Local terminal; `--watch-files` picks up `# … AI!` comments in your editor | None (local only) | Chat-turn based | *architect* mode separates plan from edit |

### 2b. Revise loop, onboarding, memory, verification

| System | 5. Revise loop (the real mechanism) | 6. Repo onboarding cost | 7. Persistent context | 8. Verification |
|---|---|---|---|---|
| **Copilot cloud agent** | `@copilot` in a PR comment → pushes commits **directly to the PR branch**. "Copilot remembers context from previous sessions on the same pull request." Docs tell you to **batch** comments via *Start a review* rather than posting singly. Only users with write access can trigger | Org/repo-level Copilot; `copilot-setup-steps.yml` for deps; custom agents at `.github/agents/*.md` (also org-level in `.github`/`.github-private`) | `.github/copilot-instructions.md`, AGENTS.md, path-specific instructions, custom agents, MCP | Runs tests in its ephemeral GH-Actions env; agentic code review can hand findings to the coding agent to open fix PRs (blog, secondary) |
| **Devin** | PR comments re-enter the session. **Bot comments are ignored by default** to prevent feedback loops; org-level allowlist opts specific bots in; comments containing `lint check failed` are *always* processed. `Devin Review` + **Auto-Fix** proposes commits alongside findings | Index the repo (branch-scoped, "a few minutes"), plus a separate environment setup / blueprint. Org admin installs the GitHub integration once and picks repos | **Knowledge** (trigger-description retrieval, scoped org/enterprise/repo/user, auto-suggested from your chat feedback) + **Playbooks** (`.devin.md`, versioned, macros like `!deploy-checklist`) + AGENTS.md + DeepWiki | Guidance: "ask Devin to test its own work before opening a PR"; read/write on checks and commit statuses so it can see CI |
| **Codex** | `@codex review` posts a review (P0/P1 only, deliberately); `@codex fix the P1 issue` starts a cloud chat that **pushes corrections** if it has write permission. Automatic reviews are a per-repo toggle | Per-repo environment config (deps, env vars, secrets, setup steps) | AGENTS.md, nested per-directory, incl. a `## Code Review Rules` section that review honours | Runs in an isolated environment; review is a separate explicit pass |
| **Claude Code Action** | Interactive mode fires on `pull_request_review_comment` and `issue_comment`; Claude replies and pushes. Bot actors rejected unless in `allowed_bots` — explicitly "keeps bots from triggering Claude in a loop" | **Three steps, same as foundry**: install the GitHub App, add a secret, add a workflow file. Documented mitigation: org-level app install + org-level secret + **one reusable workflow** each repo calls | `CLAUDE.md` at repo root, read on every run; skills in `.claude/skills/`; plugins via `plugin_marketplaces` | Whatever the prompt runs; no built-in gate |
| **Claude routines / web** | **Auto-fix pull requests.** Claude subscribes to GitHub webhooks on one PR; on a CI failure or a review comment it investigates, and: *clear fix* → change, push, explain; *ambiguous or architecturally significant* → **asks you first**; *duplicate/no-op* → notes and moves on. Per-PR toggle, turned on from web, `/autofix-pr` in the terminal, or by telling Claude on the **mobile app**. Known hole: no webhook when the base branch advances, so it cannot see merge conflicts | Claude GitHub App install (required for auto-fix webhooks) + a cloud environment (network policy, env vars, cached setup script) | Repo's `CLAUDE.md`, committed `.claude/agents/`, committed `.mcp.json` | Cloud environment runs the repo's tests; **run status green only means the session exited, not that the task succeeded** — the docs say this outright |
| **Jules** | **CI Fixer** (Feb 2026): detects and fixes GitHub Actions failures "in a continuous improvement loop". PR-review-comment handling not documented on the pages I fetched — **unverified** | Authorise GitHub, pick repo + branch, optional setup script | AGENTS.md at repo root | Runs in a VM (20 GB disk); CI Fixer closes the loop on Actions |
| **Cursor** | Follow-up messages to a running agent; team follow-ups gated by admin. Bugbot "Agentic AutoFix" — **secondary source only, unverified** | Admin connects the SCM org once; `.cursor/environment.json` (snapshot / install command / terminals) per repo | `.cursor/rules`, AGENTS.md (per agents.md) | VM can build, test, take screenshots/videos, drive a remote desktop |
| **Factory** | Automated Code Review + CI automations; `droid exec` in CI. A dedicated review-comment→fix loop is **unverified** | Connect repo; Droid Computers / cloud templates; `AGENTS.md` | AGENTS.md, Skills, custom slash commands, subagents, hooks, plugins, **AutoWiki** (auto-refreshing repo wiki) | Missions "test work against your application as features complete"; Automated QA is its own Software Factory stage |
| **OpenHands** | `@openhands` in a **PR comment** gets assistance (source: docs excerpt via search — the page itself timed out on three fetch attempts, **partially verified**) | Install the GitHub App on repos; optional `.openhands/microagents/` | **Microagents** in `.openhands/microagents/`, with `always` / `keyword` / `manual` trigger types; `repo.md` as the codebase mental model | Sandboxed runtime runs tests before opening the PR |
| **gh-aw** | `slash_command` and `label_command` triggers; safe outputs include `create-pull-request-review-comment`, `reply-to-pull-request-review-comment`, `resolve-pull-request-review-thread`, `push-to-pull-request-branch` | `gh extension install github/gh-aw` then `gh aw add-wizard <workflow>`; ~10 minutes, per repo | Whatever the markdown workflow and repo files carry | The workflow's own steps; plus `create-check-run` to surface results in the PR checks UI |

### 2c. Guardrails, throughput, cost, fleet

| System | 9. Guardrails | 10. Concurrency & reviewer load | 11. Cost / model routing | 12. Multi-repo fleet |
|---|---|---|---|---|
| **Copilot cloud agent** | Ephemeral GH-Actions env; only write-access users can trigger; no auto-merge documented | Agent session limits for admins (secondary source, Jul 2026). Docs push **batching review comments** as the reviewer-load answer | **1 premium request per session**, × model rate; each steering comment = 1 more; autonomous tool calls are free. Actions minutes + AI credits | Per-repo. Org/enterprise-level custom agents are the only fleet-wide artifact |
| **Devin** | Bot-comment allowlist; ACU spend limits per PR and per session; automation invocation rate caps ("maximum 10 fires per hour"); network policies; webhook secrets; security profiles; branch protection recommended | Automations have explicit rate caps; enterprise per-user ACU limits | Free / Pro $20 / Max $200 / Teams from $80 (full seat $40/mo). **Its own self-serve pricing page no longer defines what an ACU is** — pricing clarity has regressed | Repos are indexed individually; Automations can watch org-wide events. No portfolio-sweep product |
| **Codex** | Isolated cloud env; review deliberately limited to P0/P1 to protect reviewer attention | Parallel tasks; per-plan concurrency (**unverified**) | Bundled with ChatGPT plan tiers | Per-repo environments |
| **Claude Code Action** | Write-access check + bot-actor rejection on every event; `--allowedTools`; scheduled workflows only run from the default branch and auto-disable after 60 days of inactivity on public repos | `--max-turns`, `timeout-minutes`, GH concurrency controls — the docs list these under "Manage costs" | API key, subscription OAuth token, or OIDC workload-identity federation (no stored secret). Model per workflow via `claude_args: --model …` | Reusable workflows called from each repo |
| **Claude routines** | Pushes to `claude/`-prefixed branches are always accepted; **any other branch is rejected if it is protected, has someone else's open PR, or carries commits authored by someone else**; network allowlist (`403 host_not_allowed`); API `text` payload arrives wrapped in `<routine-fire-payload>` labelled untrusted | Daily per-account routine run cap; per-routine and per-account hourly caps on GitHub webhook events, excess **dropped** | Draws on subscription usage; metered overage needs "usage credits" on. **Requires a claude.ai subscription login — API-key accounts are explicitly unsupported** | **A single routine can list multiple repositories**, each cloned per run. The closest hosted analogue to foundry's fleet model |
| **Jules** | Plan approval; Planning Critic; commit authoring modes (Jules-only / co-authored / user-only) | 3 / 15 / 60 concurrent tasks by tier; limits are per-user, not pooled | Free / Google AI Pro / Google AI Ultra. **Docs disagree with themselves**: the usage-limits page says all tiers use Gemini 2.5 Pro, while the changelog says Gemini 3 Flash became the base model (2026-01-30) and Gemini 3.1 Pro the Pro default (2026-03-09). Treat the limits page as stale | Per-repo |
| **Cursor** | Admin connects SCM; read-only shared runs by default | Parallel agents; unlimited-ish, cost-bounded | Model API pricing, spend limit set at setup | Multi-repo support for coordinated changes named on the cloud-agent page |
| **Factory** | Autonomy levels off/low/medium/high; Droid Shield; sandbox; airgapped deployment; enterprise managed settings | Missions decompose into parallel tracks; `droid exec` composes for parallel work | Pro $20 / Plus $100 / Max $200; three rolling limit windows (5h / 7d / 30d); BYOK; Factory Router for per-task model choice | "Software Factory" is org-wide by framing, but **Triage — the intake stage — is Private Preview, contact-sales only** |
| **OpenHands** | Sandboxed runtime; MIT licence; self-hostable | Unlimited daily conversations (Individual, free); unlimited concurrent only on Enterprise | OSS free; Cloud Individual free with at-cost BYO-or-hosted models; Enterprise custom | Per-repo App install |
| **gh-aw** | **The best-designed guardrails in the survey.** Agent job runs read-only and buffers output as an artifact; a separate AI **threat-detection job** scans it; only then do narrowly-scoped write jobs run. "The agent never requires write permissions." Content sanitised on the way in (`@user` → `` `@user` ``). Egress via an iptables + Squid domain allowlist | Every safe output has a `max:` (create-issue defaults to **1**), plus `concurrency-group`, `group-reports`, dedupe and auto-expiration | Engine-selectable: Copilot (default), Claude, Codex, Gemini, Pi, custom | **Yes — the only one built for it.** Safe outputs take `target-repo` and `allowed-repos`; `dispatch-repository` fires cross-repo `repository_dispatch`; `failure-issue-repo` routes run failures to a hub repo |

---

## 3. Per-system notes worth the user's attention

Ranked by relevance to foundry.

### GitHub Agentic Workflows (`gh-aw`) + `githubnext/agentics` — read this first
<https://github.github.io/gh-aw/> · <https://github.com/githubnext/agentics>

This is foundry's architecture, built by GitHub Next, in the open. Workflows are markdown
with YAML frontmatter (`on:`, `permissions:`, `engine:`, `tools:`, `safe-outputs:`)
compiled into GitHub Actions. The security model is the same conclusion foundry reached
independently — **the model never holds a write token** — but taken one step further with
an AI threat-detection job between the agent and the writers, plus input sanitisation and
a Squid-proxy egress allowlist.

`agentics` ships ready-made: *Daily Repo Status* (≈ L0), *Daily Plan* (≈ L0's next-steps),
*Repo Assist* ("issue triage, investigation, bug fixes, activity summaries" ≈ L1+L2),
*CI Doctor* (≈ L3's red-CI hunt), *Cost Tracker*, *Weekly Issue Activity*.

Caveat before anyone gets excited: it is a GitHub Next project, the docs mix "experimental"
and "GA" features, and cross-repo `dispatch-repository` is flagged experimental. Adopting
it means rewriting four working loops in someone else's DSL.

### Claude Code on the web — routines + auto-fix
<https://code.claude.com/docs/en/routines> · <https://code.claude.com/docs/en/claude-code-on-the-web>

Two mechanisms here matter.

**Routines** are hosted cron-plus-webhook-plus-API agent runs over a list of repositories.
They are the hosted version of foundry's L0/L1/L3, and they include a branch-push guard
worth copying verbatim: `claude/`-prefixed branches are always accepted, and a push to any
other branch is refused if it is protected, has someone else's open PR, or carries commits
authored by someone else. That is a mechanical enforcement of foundry's "never destroy the
user's work" rail.

Two blockers for foundry: routines are in **research preview**, and they require a
claude.ai subscription login — "API accounts aren't supported for routines". That directly
conflicts with foundry's deliberate choice of a metered API key over the Pro OAuth token.

**Auto-fix pull requests** is the single most stealable mechanism in this whole survey.
See §6.1.

### Devin
<https://docs.devin.ai/product-guides/automations> · <https://docs.devin.ai/product-guides/bot-comment-settings> · <https://docs.devin.ai/product-guides/creating-playbooks> · <https://docs.devin.ai/product-guides/knowledge>

The most mature *operational* thinking of anyone. Automations decompose cleanly into
**trigger → conditions → action**, with four action types including "message an existing
long-running session" (i.e. a revise loop as a first-class action) and "Triage Devin", a
persistent channel monitor that spawns child sessions. Safeguards are per-automation:
ACU budget, invocation rate cap, network policy, webhook secret.

The bot-comment page is the one page in this survey written by someone who has been bitten:
default is *ignore all bot comments* to prevent feedback loops, with an explicit allowlist
and one hardcoded exception (`lint check failed` always processed).

Playbooks vs Knowledge is a distinction foundry has half-made: Playbooks are procedures you
invoke (`!macro`, versioned `.devin.md`); Knowledge is retrieved automatically by trigger
description. Foundry's LESSONS.md is Knowledge; its prompt files are Playbooks. Notably,
Devin's docs have **no pruning or expiry story** for Knowledge — foundry's 30-entry
not-append-only budget is better.

### GitHub Copilot cloud agent
<https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-github> · <https://docs.github.com/copilot/how-tos/agents/copilot-coding-agent/best-practices-for-using-copilot-to-work-on-tasks>

The most boring and therefore most instructive. Assign an issue → agent works → raises a PR
→ requests your review → you comment `@copilot` → it pushes to the branch, carrying context
from previous sessions on that PR. Billing is refreshingly honest about where the cost is:
**one premium request per session, one per steering comment, autonomous tool calls free** —
i.e. GitHub prices *your attention*, not the agent's work. The best-practices page's answer
to reviewer overload is "batch them by clicking Start a review".

### Jules
<https://jules.google/docs/changelog/> · <https://jules.google/docs/usage-limits/>

The only system with a **mandatory plan-approval gate**, and the only one that published a
number for a second-opinion agent: the *Planning Critic* reviews auto-approved plans and cut
the failure rate 9.5%. *CI Fixer* closes the Actions-failure loop automatically. Free tier is
15 tasks/day, 3 concurrent — which is more throughput than one solo reviewer can absorb, at
$0. Its docs contradict themselves on models (see §2c); trust the changelog.

### Factory.ai
<https://docs.factory.ai/software-factory/overview.md> · <https://docs.factory.ai/missions/overview.md> · <https://docs.factory.ai/droid-exec/overview.md>

Real product, real CLI, honest docs. But the "Software Factory" it sells is an *enterprise
SDLC* — six stages, dashboards, agent-effectiveness telemetry — not a personal fleet manager,
and the intake stage (Triage) is **Private Preview, contact-sales**. The two genuinely
portable ideas: `droid exec --auto off|low|medium|high` as a graded autonomy dial that
fail-fasts on violation, and *Missions* (plan → approve → milestones → parallel tracks under
a Mission Control view). Individual pricing $20/$100/$200 with three rolling rate windows.

### OpenHands
<https://github.com/OpenHands/OpenHands> · <https://www.openhands.dev/pricing>

MIT, 86.1k stars, beta, self-hostable, free Individual cloud tier. Trigger surface is the
one foundry already has: **an issue label** (`openhands`) or `@openhands` mention.
Repo memory lives in `.openhands/microagents/` with `always` / `keyword` / `manual` trigger
types — a keyword-triggered memory file is a nicer design than one monolithic CLAUDE.md.
Its docs site timed out on every fetch attempt; the trigger details are from a search
excerpt of the doc page, so treat as **partially verified**.

### Codex, Cursor, Ona, Aider — briefly
- **Codex**: `@codex review` / `@codex fix the P1 issue`, AGENTS.md with a `## Code Review Rules` section, per-repo environments. Notable discipline: GitHub reviews surface **only P0/P1** on purpose.
- **Cursor cloud agents**: strongest breadth of launch surfaces (Web, iOS, Slack, GitHub/Bitbucket comments, Linear, API), `.cursor/environment.json` per repo.
- **Ona** (ex-Gitpod): site header reads "Part of OpenAI"; the June-2026 acquisition date is secondary-source only. Agents run in *your* infra. Enterprise-shaped; GA status **unverified**.
- **Aider**: not a factory, but its `# … AI!` in-file comment trigger is the cheapest intake surface anyone has built — the task is written where the work is.

### AGENTS.md as the emerging standard
<https://agents.md/>

Over 60,000 open-source repos; now stewarded by the Agentic AI Foundation under the Linux
Foundation. Supported by Codex, Jules, Cursor, Aider, VS Code, Copilot, JetBrains Junie,
Factory, Devin, Zed, Warp and others. Nested files, closest-wins. This matters for §7: a
repo's standing intent written as AGENTS.md is portable to *every* builder, which makes
swapping foundry's L2 for a third-party builder much less lossy than it sounds.

---

## 4. What foundry already gets right

Honest assessment, not flattery. Four of these are genuine convergent evolution; two are
better than what shipped.

1. **The model never holds a write token; caps and dedupe are enforced in Python before
   and after the model step.** This is exactly gh-aw's SafeOutputs architecture — read-only
   agent job, buffered output, separate scoped write jobs — arrived at independently. It is
   the single strongest design decision in foundry and it matches the most security-serious
   thing GitHub has shipped.
2. **Caps live in the publisher, not the prompt.** gh-aw defaults `create-issue` to
   `max: 1`; Devin caps automation invocations per hour. Everyone who has run this in anger
   throttles at the publisher. Foundry's 2-open-proposals-per-repo cap is the same instinct.
3. **Draft PRs only, nothing auto-merges.** Universal. No working system auto-merges by
   default.
4. **Model routing is already correct.** Haiku on the wide read-only sweeps (L0, L3),
   Sonnet on the narrow write path (L1), plus a `factory:deep` label to escalate one issue.
   That matches Factory's per-task Router and Jules' Flash-base/Pro-thinking split. Foundry
   also already has `--max-turns` (40/60/30) and `timeout-minutes` on every workflow — which
   is exactly what Claude's own cost-management guidance prescribes.
5. **LESSONS.md is better than any shipped memory feature.** Devin Knowledge, Copilot
   custom instructions, OpenHands microagents and AGENTS.md all accumulate; none of them
   document a pruning story. Foundry's "budget 30 entries, not append-only, evict and say
   why in the PR body" is the rot-prevention mechanism the industry hasn't built.
6. **"Never destroy the user's work" is a rail nobody else has**, and it was earned from a
   real defect (L3 proposing to delete a 21-commit branch). The closest analogue anywhere is
   Claude routines' push guard, which refuses branches carrying someone else's commits.
7. **The evidence rule is stricter than anything shipped.** Codex's P0/P1-only filter and
   gh-aw's dedupe are attention-protection; "cite a path, a line, or a commit or don't open
   the issue" is a stronger form of the same idea, and it is the right one for a reviewer
   who has one phone-minute per item.

Where the self-assessment should be less comfortable: **L2 has never run.** Every other
system in this survey is judged on behaviour; L2 is judged on a prompt. The most likely
first failure is mundane — dependency install in the runner — which is precisely why
Copilot ships `copilot-setup-steps.yml`, Cursor `.cursor/environment.json`, Devin
environment blueprints, and Claude cached setup scripts. Four independent products all
built the same thing; foundry has nothing there.

---

## 5. What foundry is missing that everyone else has

Ranked by (universality × cheapness to close).

**1. A revise loop. → gap #2. Every single working system has one.**
Copilot pushes to the PR branch on `@copilot` and remembers prior sessions on that PR.
Claude auto-fix subscribes to PR webhooks and pushes on CI failure or review comment.
Devin re-enters on PR comments. Codex does `@codex fix the P1 issue`. Jules has CI Fixer.
This is the most universal missing feature and among the cheapest to build, because L2's
builder already exists — it needs a second trigger and a different prompt preamble.

**2. Human-initiated intake as the *primary* path. → gap #1.**
Foundry has the field's flow exactly inverted. In every product, backlog scanning is the
*side* feature and "a human hands over a task" is the front door. Copilot: assign an issue.
OpenHands: apply a label. Devin/Cursor: Slack mention. gh-aw: `label_command`.

The good news is that foundry is closer than the gap statement suggests: **L2 already fires
on `issues.labeled == factory:approved`, and `scripts/factory_labels.py` already provisions
that label in every elected repo.** A hand-written issue plus that label from the GitHub
mobile app is *almost* intake today. What blocks it is L2's prompt, which opens with
"Verify the premise, first. Open the file the **Why now** line cites… If it no longer says
what the issue claims — stop." A phone-written issue has no Why-now citation, so L2 would
stop. This is a prompt branch, not a system.

**3. A plan gate inside the builder, or a critic over the plan. → new.**
Jules requires plan approval before code and runs a Planning Critic over auto-approved
plans (9.5% fewer failures). Factory has Spec Mode and Missions. Foundry's approval happens
at the *proposal* and then L2 runs unsupervised to a draft PR. For anything non-trivial the
distance between "I approved this idea" and "here is 400 lines" is where review capacity gets
burned.

**4. Self-verification as a gate, not an instruction. → new.**
Devin: "ask Devin to test its own work before opening a PR." Copilot and OpenHands run tests
in the sandbox before the PR. Foundry's L2 prompt says "if the tests fail, do not open the PR"
and demands a "still stubbed" section — good, but it is the model policing itself. Nothing
in the Python publisher checks. Claude's own docs warn that a green run status "does not mean
the task in your prompt succeeded."

**5. Per-repo environment/setup declaration. → gap #3, and a latent L2 blocker.**
`copilot-setup-steps.yml`, `.cursor/environment.json`, Devin blueprints, Claude cloud
environment setup scripts (cached). Four for four. Foundry has none, and L2 has never run.

**6. Cheap repo onboarding. → gap #3.**
Everyone else solves this with an org-level app install plus one central config. Claude's
docs name the exact mitigation for foundry's 3-step problem: install the GitHub App once at
org level, store the secret as an *organization* Actions secret, and define the job once as a
**reusable workflow** that each repo calls in five lines. That is 3 steps → 1. Zero steps is
also available: run L2 in the hub on `workflow_dispatch`/`repository_dispatch` and clone the
target, exactly as L1 already does.

**7. Failure visibility. → new.**
gh-aw has `report-failure-as-issue` and `failure-issue-repo`. When a loop errors in foundry
it dies in a run log the user will never open on a phone. This is a ~20-line change.

**8. A cost meter.**
`agentics` ships a *Cost Tracker* workflow. Foundry has a $12/mo budget and no instrument.

---

## 6. Steal list

Ordered by value per hour of build. "Cost" is agent-hours, not human weeks.

### 6.1 Auto-fix-shaped revise loop — **steal this first**
**What:** a workflow on `pull_request_review_comment.created` and `issue_comment.created`
(PR-scoped), restricted to PRs the factory opened, that re-enters L2's builder with the
review thread as its task. Three outcomes, copied from Claude's auto-fix triage: *clear fix*
→ commit and push to the same branch, reply in-thread; *ambiguous or architecturally
significant* → do not guess, reply with the one question and apply `factory:blocked`;
*no-op* → react and stop.
**Who:** Anthropic (auto-fix PRs), GitHub (`@copilot`), Devin, Codex, Jules.
**Why it fits:** L2's prompt, rails and PR-body discipline already exist; this is a second
trigger and a preamble. It also directly serves the stated job of increasing PR throughput —
today a draft PR that needs one change is a dead end.
**Cost:** low. One workflow file, one prompt file, one publisher branch.

### 6.2 Bot-comment allowlist and a per-PR revise budget
**What:** before 6.1 ships, decide who can trigger it. Default: only the repo owner. Ignore
all bot comments unless allowlisted. Hard-cap revise runs per PR (3 is plenty) and refuse to
re-enter a PR the user has not touched since the last revise.
**Who:** Devin (default = ignore all bots, "risks infinite loops"); Claude Code Action
(`allowed_bots`, "keeps bots from triggering Claude in a loop"); Copilot (write-access only).
**Why it fits:** foundry runs on a metered key with a $12 budget. A loop that answers its own
comment is the failure mode that turns that into a bill.
**Cost:** trivial, and it is prerequisite insurance for 6.1.

### 6.3 `factory:do-this` — a second, human-authored intake label
**What:** a label distinct from `factory:approved`, meaning "I wrote this myself, it has no
L1 evidence block, build it anyway". L2's prompt branches on it: skip the premise-verification
step, keep every other rail. Add it to `VOCABULARY` in `scripts/factory_labels.py`.
**Who:** OpenHands (`openhands` label), gh-aw (`label_command`), Copilot (issue assignment).
**Why it fits:** closes gap #1 with zero new surface, zero new auth, and it works from the
GitHub mobile app in two taps. The plumbing is already built and already deployed.
**Cost:** trivial — a label, a prompt branch, and a line in the workflow's `if:`.

### 6.4 A planning critic in the publisher
**What:** before L1 publishes a proposal (and optionally before L2 commits to a plan), one
extra cheap-model call whose only job is to reject: does this contradict LESSONS.md, does the
cited evidence actually support the claim, is the done-gate a user-observable transaction.
Reject → write nothing. Foundry's CLAUDE.md already says writing nothing is a valid outcome.
**Who:** Jules' Planning Critic (published 9.5% failure-rate reduction); gh-aw's separate
threat-detection job between agent and writer.
**Why it fits:** the binding constraint is the user's review minute. Anything that turns a
bad proposal into silence is worth more than anything that increases throughput.
**Cost:** low. One Haiku call inside `propose_publish.py`.

### 6.5 Failure-as-issue
**What:** when any loop's run fails, open (or update) one issue in the hub naming the loop,
the run URL and the error. Dedupe on a stable key so a persistent failure does not spam.
**Who:** gh-aw `report-failure-as-issue` / `failure-issue-repo`; Devin automation email
notifications on failure.
**Why it fits:** the user reviews on a phone, in the morning, in GitHub. A red Actions badge
in a hub repo they do not open is not a notification.
**Cost:** trivial.

### 6.6 Per-repo setup declaration
**What:** a `setup:` block per repo — either a new field in `PROJECTS.md` or a
`.factory/setup.sh` in each target — that L2 runs before it starts. Install command, test
command, anything version-pinned.
**Who:** `copilot-setup-steps.yml`, `.cursor/environment.json`, Devin environment blueprints,
Claude cloud environment setup scripts (cached between runs).
**Why it fits:** L2 has never run. Four independent products shipped this because
trial-and-error dependency discovery is where cloud builders fail first.
**Cost:** low, and it is the cheapest de-risking of L2's first real run.

### 6.7 Reusable workflow + org-level secret (or move L2 into the hub)
**What:** define the L2 job once in the hub as a `workflow_call` reusable workflow; each
target repo gets a five-line caller and no secret of its own (org-level Actions secret).
Better still: run L2 in the hub on `repository_dispatch` and clone the target, like L1.
**Who:** documented explicitly in Claude Code Action's "Set up for an organization".
**Why it fits:** closes gap #3 and removes the per-repo secret copy, which is also the
riskiest manual step.
**Cost:** medium. Real refactor of where L2 lives, worth doing *before* onboarding repo #7.

### 6.8 Branch-push guard, mechanised
**What:** enforce in Python what CLAUDE.md currently states in prose: the factory may push
only to `claude/`- or `factory/`-prefixed branches; any other target is refused if it is
protected, has an open PR from someone else, or carries commits not authored by the factory.
**Who:** Claude routines' branch permission rules, verbatim.
**Why it fits:** foundry's most-earned rail — "never destroy the user's work" — is currently
a rule the model is asked to follow. This makes it a rule the model cannot break.
**Cost:** low.

### 6.9 Carry the plan forward on the PR
**What:** L2 posts its plan as a PR comment; the revise loop (6.1) reads it instead of
re-deriving intent from the diff.
**Who:** Copilot — "remembers context from previous sessions on the same pull request."
**Cost:** trivial, and it makes 6.1 meaningfully better.

### 6.10 A cost tracker loop
**What:** weekly, post token spend per loop per repo to the hub.
**Who:** `githubnext/agentics` Cost Tracker.
**Cost:** low. Worth it only once 6.1 exists, since revise loops are what will actually
threaten a $12 budget.

---

## 7. Wholesale vs cherry-pick — and the case against foundry

### Position: cherry-pick the mechanisms, and shrink foundry to what only foundry does.

**Do not adopt any product wholesale.** Every candidate fails on at least one hard
constraint. Routines are research preview and forbid API-key auth, which is foundry's
explicit choice. Factory's Triage is contact-sales Private Preview. Claude Tag is Slack-only,
Team/Enterprise-only. Devin's cheapest useful tier is $20/mo with pricing units its own docs
no longer define. gh-aw would mean rewriting four working loops in a GitHub Next DSL that
mixes experimental and GA surfaces.

**Do not migrate to gh-aw — but read its safe-outputs reference as a specification.** It is
the same architecture foundry already has, further along. Take `target-repo`/`allowed-repos`
framing, the `max: 1` default posture, `failure-issue-repo`, and the idea of a separate
critic job between the agent and the writers. Leave the DSL.

### Now the pushback, because it is real.

**The strongest argument against foundry is not "buy something instead". It is "you built
three loops that are genuinely rare and one loop that is a commodity, and the commodity one
is eating your budget and your onboarding cost."**

L2 is:
- the only loop that lives inside target repos, and therefore the entire source of gap #3;
- the only loop that has never run, so its quality is unmeasured;
- the loop that needs the revise mechanism, the plan gate, the self-verification gate and the
  per-repo environment — i.e. four of the six things §5 says are missing exist *only* to
  serve L2;
- and the loop that four GA products already do well. Jules does it free, with a mandatory
  plan gate, a planning critic and a CI fixer. Copilot does it for one premium request per
  session, with a revise loop, and it reads AGENTS.md.

Meanwhile L0 is genuinely unmatched. Nothing on the market answers "across my twelve repos,
which one should I re-enter and where". Routines can be pointed at several repositories and
gh-aw can write cross-repo, but the *product* framing everywhere — without exception — is
"give the agent a task". The cold-start-killer is the moat, and it is L0 plus PROJECTS.md,
not L2.

**So the sharpest version of the recommendation is:** let L1's approved proposal be handed to
an off-the-shelf builder instead of built by L2. Concretely — L1 already writes an issue with
What / Why now / Done-gate / Blast radius. Assign that issue to Copilot, or hand it to Jules.
Both then supply the revise loop, the plan gate and the sandbox for free, and gap #3
evaporates because there is no per-repo workflow or secret to install. Mirror foundry's rails
into each repo's `AGENTS.md`, which Copilot, Jules, Codex, Cursor, Devin and Factory all read.

**The honest counter-argument, which the user should weigh:** the rails are the product. The
"never destroy a branch", "evidence or silence", "still stubbed section", "surgical changes"
rules were earned from real defects in this specific fleet, and an AGENTS.md is advisory
where foundry's Python publisher is mechanical. Copilot will not refuse to open a PR because
a citation went stale; L2's prompt does. If the rails matter more than the throughput — and
on the evidence of LESSONS.md they might — keep L2 and pay the onboarding cost.

**A defensible middle, and my actual recommendation:**

1. Ship 6.2 + 6.3 + 6.5 this week. Trivial cost, closes the intake gap and makes failures
   visible. (Intake gap #1 → done.)
2. Ship 6.1 + 6.9. This is the biggest single throughput win and the field's most universal
   feature. (Revise gap #2 → done.)
3. Ship 6.6, then **run L2 once, for real**, on the smallest approved issue in the most
   familiar repo. Everything in §5 about L2 is speculation until it has run.
4. Only then decide 6.7 vs. outsourcing L2 — and decide it on evidence from step 3, not on
   architecture taste. If L2's first three PRs are good, do 6.7 and keep it. If they are
   not, assign the next approved issue to Copilot or Jules and compare the two PRs directly.
   That is a cheap, decisive experiment and it is the right way to settle this.

One more piece of pushback: **the user's belief that review capacity is the real bottleneck
is correct, and it is also the field's consensus.** GitHub prices a session at one premium
request and charges again for each steering comment — it is billing attention. Codex
deliberately surfaces only P0/P1 findings. Copilot's documented answer to reviewer overload
is "batch your comments". Devin caps automations at N fires per hour. Not one of these systems
tries to maximise PR throughput. That is worth holding onto: **"increase PR throughput" is a
job that will fight the other two jobs**, and of the ten steals above, the ones that pay best
(6.2, 6.4) reduce output rather than increase it.

---

## 8. Sources

Fetched during this research. Grouped by system.

**Factory.ai**
- https://docs.factory.ai/llms.txt
- https://docs.factory.ai/software-factory/overview.md
- https://docs.factory.ai/software-factory/automations.md
- https://docs.factory.ai/software-factory/triage.md
- https://docs.factory.ai/missions/overview.md
- https://docs.factory.ai/autonomy-and-safety/specification-mode.md
- https://docs.factory.ai/droid-exec/overview.md
- https://docs.factory.ai/pricing/individuals.md

**Devin / Cognition**
- https://docs.devin.ai/llms.txt
- https://docs.devin.ai/product-guides/automations.md
- https://docs.devin.ai/product-guides/scheduled-sessions.md
- https://docs.devin.ai/product-guides/creating-playbooks.md
- https://docs.devin.ai/product-guides/knowledge.md
- https://docs.devin.ai/product-guides/bot-comment-settings.md
- https://docs.devin.ai/work-with-devin/devin-review.md
- https://docs.devin.ai/integrations/gh.md
- https://docs.devin.ai/integrations/slack.md
- https://docs.devin.ai/onboard-devin/index-repo.md
- https://docs.devin.ai/essential-guidelines/when-to-use-devin.md
- https://docs.devin.ai/essential-guidelines/instructing-devin-effectively.md
- https://docs.devin.ai/admin/billing/self-serve.md

**GitHub Copilot**
- https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent
- https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-github
- https://docs.github.com/copilot/how-tos/agents/copilot-coding-agent/best-practices-for-using-copilot-to-work-on-tasks
- https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-custom-agents
- https://docs.github.com/en/copilot/concepts/billing/copilot-requests
- https://docs.github.com/en/copilot/reference/ai-models/model-comparison

**GitHub Agentic Workflows (gh-aw) / agentics**
- https://github.github.io/gh-aw/
- https://github.github.io/gh-aw/introduction/architecture/
- https://github.github.io/gh-aw/gallery/
- https://github.github.io/gh-aw/setup/quick-start/
- https://github.github.io/gh-aw/reference/safe-outputs/
- https://github.github.io/gh-aw/llms.txt
- https://github.com/github/gh-aw/blob/main/.github/aw/triggers.md
- https://github.com/githubnext/agentics

**Anthropic / Claude**
- https://code.claude.com/docs/en/github-actions
- https://code.claude.com/docs/en/claude-code-on-the-web
- https://code.claude.com/docs/en/routines
- https://claude.com/docs/claude-tag/overview

**OpenAI Codex**
- https://learn.chatgpt.com/docs/cloud
- https://learn.chatgpt.com/docs/code-review
- https://learn.chatgpt.com/docs/third-party/github

**Google Jules**
- https://jules.google/docs
- https://jules.google/docs/changelog/
- https://jules.google/docs/usage-limits/

**Cursor**
- https://cursor.com/docs/cloud-agent

**OpenHands / All Hands**
- https://github.com/OpenHands/OpenHands
- https://www.openhands.dev/pricing
- (docs.openhands.dev timed out on three attempts; trigger details are from a search
  excerpt of https://docs.openhands.dev/openhands/usage/cloud/github-installation —
  **partially verified**)

**Ona (ex-Gitpod)**
- https://ona.com/product

**Standards / other**
- https://agents.md/
- https://aider.chat/docs/usage/watch.html

**Search-only, not fetched (marked unverified in the text):** Bugbot AutoFix, Kiro pricing
and hooks, CodeRabbit/Greptile/Ellipsis pricing, Copilot agent session limits (Jul 2026),
Ona/OpenAI acquisition date, `mini-swe-agent` production adopters, Copilot Workspace status.
