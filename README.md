# Foundry

A personal software factory. It runs on GitHub Actions, watches a short list of my
own repositories, and does three things on a schedule: notice what needs doing,
propose it, and — only after I say yes — build it.

Nothing here merges itself. Every loop stops at a draft PR or an issue waiting on a
label. The one irreversible step is me tapping a button.

## Why it exists

I have more projects than review time. The bottleneck isn't writing code, it's
deciding what's worth writing. So the factory spends its runs on the deciding part:
it reads the repos, cites what it found, and hands me a short list. A run that
produces nothing is a normal outcome, not a failure.

## The loops

Each is a workflow in `.github/workflows/`. The `L0`–`L3` names are just an ordering
— survey, propose, build, maintain.

| Workflow | Plain English | When |
|---|---|---|
| `factory-census.yml` (L0) | Surveys every tracked repo and writes down where each one actually stands. | Mondays 06:00 UTC |
| `factory-proposer.yml` (L1) | Reads the survey and opens issues proposing specific next steps, each with a citation. | Tue/Thu/Sat 06:00 UTC |
| `factory-build.yml` (L2) | Picks up issues I've approved and opens a draft PR implementing them. | Hourly, :07 |
| `factory-keepwarm.yml` (L3) | Keeps stalled work from rotting — surfaces it, never deletes it. | Wednesdays 06:00 UTC |
| `factory-inbox.yml` | Publishes `inbox/inbox.json` — the single file listing what needs me, most pressing first. | Hourly, :07 |
| `factory-labels.yml` | Copies the `factory:*` label vocabulary into a target repo. Run once per new repo. | Manual |
| `weekly-report.yml` | Cross-project activity summary from the GitHub API — commits, PRs, issues over the past 7 days. No AI. Writes `reports/YYYY-Www.md`. | Mondays 05:00 UTC |

## How I actually use it

1. In the morning, I read one file: `inbox/inbox.json`. It lists what's waiting on
   me and, for each item, the labels that answer it. (`priority-post` reads this
   file too — it's the handoff between the two projects.)
2. To approve a proposal, I add `factory:approved` to the issue. To decline it,
   `factory:declined`. That's the entire interface.
3. Within the hour, the builder picks up anything approved and opens a draft PR.
4. I review the diff and merge it myself, or I don't.

The label vocabulary: `factory:proposed`, `factory:approved`, `factory:declined`,
`factory:building`, `factory:built`, `factory:blocked`, `factory:deep`,
`factory:resume`, `factory:try-again`.

## The rails

The full charter is in `CLAUDE.md`, and it governs every run. The short version:

- **Draft PRs only.** Never merge, never push to `main`.
- **Evidence or silence.** Every proposal cites a path, a line, or a commit. No
  citation, no issue.
- **Never destroy my work.** No deleting branches, closing unmerged PRs, or
  discarding commits — regardless of age.
- **Escalate instead of guessing.** Uncertainty becomes `factory:blocked` with one
  specific question.
- **No self-modification.** A run may propose changes to these workflows through a
  normal reviewed PR. It may never edit them mid-run.
- **Secrets never surface.** Not printed, not logged, not masked.

## Layout

    .github/workflows/   the loops
    CLAUDE.md            the operating charter every run reads
    docs/factory/
      PROJECTS.md        what each tracked repo is and what "done" means for it
      LESSONS.md         what previous runs got wrong, so they stop repeating it
    inbox/inbox.json     the published list of what needs me
    repos.txt            which repositories the factory watches
    reports/             weekly activity reports
    scripts/, tests/     the Python behind the inbox and the reports

## Cost and credentials

Runs use a metered Anthropic API key held as a repository secret — never a personal
OAuth token.
