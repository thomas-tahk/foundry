# Design — Say it in plain English

**Date:** 2026-09-05
**Status:** approved, not implemented
**Sibling spec:** `2026-09-05-hub-builder-design.md` (do this one first)

## The problem

Everything the factory writes is written in vocabulary the factory invented for
itself. A proposal opens with **What / Why now / Done-gate / Blast radius** and closes
with `Source: pocket-draft#2 step 3`. A pull request reports under **Done-gate** and
**Still mocked, stubbed, or hardcoded**.

To read any of it you have to already know how the factory works — which inverts the
entire point of the factory, whose first job is to spare the reader exactly that kind
of loading-up.

The user, unprompted, on 2026-09-05:

> from the few I've seen so far, you really gotta make these as human readable as
> possible. some of the jargon and naming conventions are really rough to follow and I
> have to often ask you manually here many times to even get a small grasp of it

This is the second time the same complaint has landed. The first (2026-08-29) was read
as a *structure* problem — whole sections were being dropped — and the structure was
fixed. The vocabulary was never touched. It is the vocabulary.

## What changes

Prompts only, plus one regular expression. No workflow changes, no new scripts.

### 1. Rename every heading the reader sees

Applies to `.factory/prompts/l1-proposer.md`, `.factory/prompts/l3-keepwarm.md`
(identical format by design), and the pull-request template in
`.factory/prompts/l2-builder.md`.

| Written today | Written after |
| --- | --- |
| `**What**` | `**The change**` |
| `**Why now**` | `**Why I'm suggesting it**` |
| `**Done-gate**` | `**How you'll know it worked**` |
| `**Blast radius**` | `**What this touches**` |
| `**Implementation notes**` | `**Notes for whoever builds it**` |
| `## Done-gate` (PR) | `## How to check it worked` |
| `## Still mocked, stubbed, or hardcoded` (PR) | `## What's not real yet` |

`## What changed`, `## Tests`, and `## Noticed, not changed` in the PR template are
already plain and stay as they are.

The weekly survey's headings (`## State`, `## Half-done work`, `## Likely reason it
stalled`, `## Next steps`, `## Blockers`, `## Facts`) are also already plain and stay.
Its problem is tone, not labelling — covered by rule 3.

### 2. Hide the bookkeeping line

`Source: <repo>#<issue> step <n>` is a machine key. It stops the same work being
proposed twice, it is genuinely necessary, and the reader should never see it.

Move it into an HTML comment on the last line, which GitHub renders invisibly:

    <!-- Source: pocket-draft#2 step 3 -->

`scripts/propose_facts.py:20` currently reads:

    SOURCE_RE = re.compile(r"^\s*(?:\*\*)?Source:(?:\*\*)?\s*(.+?)\s*$", re.M | re.I)

`^\s*` admits only whitespace before `Source:`, so the comment form will not match and
every existing proposal would silently lose its dedupe key. The expression must accept
**both** forms — live issues today carry the bare form and must keep working — and stop
before the closing `-->`:

    SOURCE_RE = re.compile(
        r"^\s*(?:<!--\s*)?(?:\*\*)?Source:(?:\*\*)?\s*(.+?)\s*(?:-->)?\s*$", re.M | re.I)

Tested both ways in `tests/test_propose_facts.py` before anything else changes.

### 3. Ban the internal vocabulary from anything the reader reads

A rule added to all four prompts, with the same wording in each:

> You are writing for someone who did not build this system and should not have to
> learn it. Never use its internal vocabulary in anything a person reads: not loop
> names or numbers, not "census", "proposer", "keep-warm", "builder", "elected",
> "the cap", "the queue", "blast radius", "done-gate", or "Source". Name what a thing
> *is*. Label names are the one exception, and only as an instruction to act — "add the
> `factory:approved` label" is fine; describing an issue as "in factory:proposed state"
> is not.

### 4. Give each prompt a worked before/after

The established lesson from the August pass: the survey is narrated by the cheapest
model, and **examples land where prose rules do not**. Each prompt gets one short
bad/good pair showing the same finding written both ways — jargon first, plain second.

## How we'll know it worked

Run the weekly survey and the proposer by hand, then read the issue bodies they
actually wrote — not the run status. The August pass established that a green run
proves nothing here.

Per the live bodies, all of these must hold:

- Zero occurrences of the banned vocabulary list in any issue or PR body.
- Zero visible `Source:` lines; the dedupe key still parses out of all of them.
- Existing issues written before the change still parse (the old bare form).
- The 12 pinned weekly-survey issues re-render without losing a section — the upsert is
  idempotent, so re-dispatching is the safe way to test.

Then the real gate: **the user reads one proposal end to end on their phone and does
not have to ask what a word means.**

## Deliberately not doing

- **Renaming the `factory:*` labels.** They are the control surface and they sit on live
  issues; renaming means migrating them. `factory:deep` is the only genuinely opaque one
  and it is rarely used. Revisit separately if it bites.
- **Restructuring the sections.** The structure was tuned in August against live output
  and works. This change is vocabulary and tone only.
