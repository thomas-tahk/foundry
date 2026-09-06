# Design — Move the builder to the hub, and let the user talk to it

**Date:** 2026-09-05
**Status:** implemented 2026-09-06 on `factory/hub-builder`
**Sibling spec:** `2026-09-05-plain-english-output-design.md` (do that one first)

## The problem

Three of the four loops live in this repo and reach out to the projects. The builder is
the odd one out: `.github/workflows/factory-build.yml` has to be installed *inside*
every project it builds in, which costs three manual steps per project — copy the
workflow, set `ANTHROPIC_API_KEY`, install the Claude GitHub App.

Twelve projects are surveyed. One is elected. The setup tax is why.

That tax also produced the deeper failure named on 2026-09-04: every bug found and rail
written so far was generalised from a single repo's quirks. **A factory validated on
one product line is not validated.** Making election cheap is the precondition for
fixing that.

Two adjacent gaps close in the same change because they share the same machinery:

- **No way in.** The user cannot hand the factory a task. The only entrance is
  survey → proposal → approve.
- **No second pass.** The builder opens a draft PR and stops. A PR that is 90% right
  costs nearly as much as no PR, because correcting it means opening a laptop and
  context-switching into that project — the exact expense this system exists to avoid.

## The constraint that shapes the design

Today the model itself pushes the branch and opens the PR, using a token minted by the
Claude GitHub App. **That token is scoped to the repository the workflow runs in.** The
moment the workflow lives here, it can only write to this repo — it cannot push to
`pocket-draft`.

So the model cannot open the PR anymore. That is the fix, not a problem: it forces the
builder into the same three-stage shape as the other three loops, and restores a rail
the builder is currently the *only* violator of — **the model holds no GitHub token.**

## What gets built

### The workflow — `.github/workflows/factory-build.yml` (here, not in projects)

    on:
      schedule:
        - cron: "7 * * * *"
      workflow_dispatch: {}

Hourly, at seven past. Scheduled runs are best-effort and the top of the hour is the
worst time to ask, so an odd minute. Both repos are public, so Actions minutes are free
and unlimited; a run that finds nothing exits in seconds without starting a model, so an
idle poll costs nothing in either currency.

Worst case: approve at 09:05, draft PR by roughly 10:20. `workflow_dispatch` is there
for when that is too slow.

Concurrency group `factory-build`, `cancel-in-progress: false` — one build at a time
across all projects.

### Stage 1 — `scripts/build_facts.py` (no model)

Scans the elected projects for exactly two kinds of work and picks **one** per run:

1. An issue labelled `factory:approved`.
2. A pull request labelled `factory:try-again`.

Then clones the target with L1's existing logic — `--depth 50 --no-single-branch`, plus
the per-branch documentation export into `work/<repo>/.branches/<branch>/`. That export
exists because this user's design decisions live on branches they paused, and stage 2
has no Bash and so cannot query git. Reuse it; do not reimplement it.

Writes a facts file naming the work, the repo path, and — for a retry — the previous
attempt's diff and the human comments on the PR.

**Bot comments are excluded.** Reading its own or another bot's comments as instructions
is a documented way to build an infinite loop.

### Stage 2 — the model, holding nothing

`anthropics/claude-code-action@v1` following `.factory/prompts/l2-builder.md`, with
`--allowedTools Read,Write,Edit,Glob,Grep,Bash`. Bash stays — it runs the project's
tests — but there is no token in the environment, so it cannot reach the GitHub API.

It edits files in `work/<repo>/` and writes the PR body to `build/out/<repo>.md`. It
performs no git operations at all.

### Stage 3 — `scripts/build_publish.py` (no model)

Using `FACTORY_GH_TOKEN`: create or reset the branch `claude/issue-<n>-<slug>`, commit,
push, then open the draft PR or update the existing one. Flips the labels. Re-checks
every guard against live state, as the other publishers do.

**If the model reported failing tests, publish nothing** and comment on the issue
instead. A green workflow badge must never imply a task succeeded.

## Handing the factory your own task

No new label and no new entrance. The user writes an ordinary issue in the project,
describes what they want, and adds `factory:approved`. The hourly check finds it like
any other.

One thing has to change to let that through. The builder is told to open the file the
proposal's justification cites and refuse to build if the file does not back it up. A
hand-written issue has no such citation, so the check would trip.

The check exists to police *the machine's own* proposals — to stop it building on a
premise it invented and that has since gone stale. When the user is asking, the user is
the authority and the check should stand down.

The two cases are already distinguishable with no extra machinery: **a machine-written
proposal carries the hidden `Source:` marker; a hand-written one does not.** The builder
verifies the premise when the marker is present and skips that step when it is absent.

(This depends on the sibling spec having moved `Source:` into an HTML comment, but works
identically with the bare form. Either way the marker is the test.)

## Rejecting a PR and asking for another try

The user reads the draft PR, comments what is wrong, and adds **`factory:try-again`** to
the PR. Within the hour the builder re-reads the original task, the user's comments, and
its own previous attempt, then replaces the branch contents with a new attempt and
force-pushes.

**The same PR is reused,** so the whole exchange stays in one thread and attempt 1 and
attempt 2 are visible side by side. The `factory:try-again` label is removed as the new
attempt is pushed, so the label means "a retry is pending", not "this was retried".

**Capped at three attempts.** The count lives in a hidden marker in the PR body
(`<!-- attempt: 2 -->`) rather than in commit archaeology. On the fourth request the
builder comments saying the cap is reached and what it would need from the user, and
stops.

Deliberately *not* built: reading scattered inline review comments and making surgical
edits. Rebuild-with-feedback reuses everything that already exists; the surgical version
is a project of its own and is not worth it unless this proves too blunt.

## Marking finished work as finished

After a successful build the issue currently ends with **zero** labels — the workflow
strips `factory:approved`, adds `factory:building`, then strips `building` and adds
nothing. A finished issue is indistinguishable from one nobody ever looked at.

Add `factory:built` to the vocabulary in `scripts/factory_labels.py` and apply it in
stage 3 when the PR opens. Two new labels total, `factory:built` and
`factory:try-again`; the sync workflow pushes both to every elected project.

## Migration

`pocket-draft/.github/workflows/factory-build.yml` must be **deleted in the same
change**. It fires on `issues.labeled` while the hub polls for the same label — leaving
both live means every approval builds twice. The now-unused secret and App install in
that repo are harmless and can stay.

## The one real tradeoff

`FACTORY_GH_TOKEN` gains write access to code and pull requests across every elected
project, where today each project's Claude App token is scoped to that project alone.
One token, wider blast radius.

Accepting it because: the token lives only in this repo's secrets and is never handed to
a model; stage 3 is a fixed Python script with no model in the loop; and the same token
already opens issues in all twelve projects. But it is a real widening and the user
should agree to it explicitly rather than discover it later.

## What the user has to do, and when

Before the first run — **the permission change comes first, or stage 3 fails at the
push**:

1. Edit `FACTORY_GH_TOKEN`'s fine-grained permissions to add **Contents: read and
   write** and **Pull requests: read and write**. Editing a fine-grained token's
   permissions does *not* change the token value — no regenerate, no re-paste of the
   secret. (Learned the hard way during the first bootstrap.)
2. Run **Factory — Sync labels** to push `factory:built` and `factory:try-again` out.

## How we'll know it worked

Not "the tests pass" and not "the run is green". In order:

1. Approve an issue in `pocket-draft`. Within roughly an hour a draft PR exists, opened
   by the hub, and the issue reads `factory:built`.
2. Comment a real objection on that PR and add `factory:try-again`. Within roughly an
   hour the same PR carries a second attempt that answers the objection.
3. Write an issue by hand — no citation, no proposal format — approve it, and get a PR
   for it.
4. **The gate:** add a second project to `elected.txt`, change nothing else, and get a
   proposal and then a build out of it. That is the claim this whole spec makes, and it
   is also the first honest test of whether the factory is portable or merely
   pocket-draft-shaped.

## Deliberately not doing

- **Instant triggering.** A forwarding workflow in each project would fire immediately
  but keeps a per-project file, which is the complaint that started this.
- **Building more than one thing per run.** One at a time keeps the log readable and the
  review queue honest.
- **Touching the proposer, survey, or keep-warm patrol.** They already work this way.
