# Lessons

What has and has not worked across these projects. Read this before proposing anything.
A proposal that contradicts a lesson here must say so and argue the case, or not be
opened.

**Budget: 30 entries, one line each plus a link. This file is not append-only.** To add
an entry when the file is full, consolidate two existing entries or evict one, and say
which and why in the PR body. Append-only is how a brain becomes a swamp.

## Selection — what is worth building

1. **Synthetic demos get parked.** Four projects in a row were built on an invented
   premise and abandoned before shipping: Relay, a ServiceNow PDI demo, itsm-triage, and
   a grounded-support RAG. The category was the problem, not the execution.
2. **Build what you actually use.** Intrinsic pull is the strongest predictor of a
   project reaching "done." A tool the user opens daily survives; a portfolio piece
   built to be looked at does not.
3. **Prefer checkable ground truth.** Work where correctness is externally verifiable
   (odds, an accept/reject signal, a passing end-to-end run) beats work graded by "does
   this seem right to me."
4. **A weak premise is not fixed by better execution.** itsm-triage was clean, tested,
   and green — and still unconvincing, because its labels were org-specific policy the
   author had no authority to define. Check the premise before proposing the work.

## Verification — what counts as done

5. **A green unit test is a weaker signal than an end-to-end reproduction.** Unit tests
   frequently guard the wrong thing. Reproduce the behavior the way a user hits it.
6. **State the done-gate as one user-observable transaction.** Not "tests pass," not
   "PR merged" — those are inputs. "I sign in with my real account and see my real data"
   is a gate.
7. **When any agent reports success, ask what is still mocked, stubbed, or hardcoded**
   on the path the gate describes. This has caught real gaps more than once.
8. **Silent no-ops are the dangerous failure.** A knowflow seed script was a no-op under
   `vite-node` because of an `argv[1]` guard — it exited 0 and shipped nothing. The fix
   was a separate entrypoint plus a test that spawns the real command. Test the command
   you actually run, not the function it calls.

## Deployment — how things actually break

9. **Order is migrate → deploy → seed.** Doing it in any other order in knowflow would
   have failed; this is the sequence that worked.
10. **Code and content deploy on separate tracks.** In knowflow, merging a PR never
    updates flow content — only an explicit seed command does. Do not assume a merge
    ships data.
11. **Free-tier databases pause and do not self-wake.** Supabase pauses at ~7 days idle.
    A scheduled keepalive is required, and must be verified end-to-end, not assumed.

## Process

12. **Discuss stack and approach before scaffolding or installing anything.**
13. **Default to minimal.** Recommend the smallest thing that works; defer decisions
    that can wait. Do not layer complexity preemptively.
14. **Three similar lines is fine.** Do not abstract prematurely; a pattern worth naming
    is a different thing from repetition.
15. **A clunky-but-working first cut is a legitimate iteration zero** for exploratory
    work. Hold the intent firm, keep the stack loose, improve from there.
16. **For visual work, build it and run it.** Do not seek approval on prose or tables
    describing a UI — produce the running thing.
