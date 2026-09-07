# Projects

What each tracked project is, where it stands, and the one transaction that proves it
works. Read this before proposing work in any repo. Budget: one five-line entry per
repo. This file is not append-only — when a project is retired, delete its entry.

Format:

    ## <repo>
    **Is:** <one line — what the thing is>
    **Stands:** <one line — the current state, with a citation: a branch, a path, a PR>
    **Wants:** <the user's own words about where this project sits for them: how much
    they want it, what they want out of it next, and whether they want it at all. This
    decides which of several true next steps is worth raising. When it says a project
    is on hold or retired, propose nothing.>
    **Decided:** <optional — an architecture the user has already locked, and where they
    wrote it down. Never propose an approach that contradicts one of these.>
    **Done when:** <one user-observable transaction that proves it works>

---

## pocket-draft
**Is:** Pokémon TCG Pocket draft tool plus a Go rules engine that plays drafted decks.
**Stands:** `feat/draft-mode-flow` is 21 commits ahead of `main`, open as draft PR #7, and contains all of the stale PR #1; the draft → deckbuild → play loop runs end to end locally, but the opponent still plays a hardcoded preset (`server/carddata.go:185-190`) and no card effects exist (`engine/types.go:63` — "Vanilla cards have only this — no special text").
**Wants:** Ambitious and wanted, but the near target is a minimal working state — playable, with online matching if it can be reached.
**Decided:** Card effects use **Approach A — a shared primitive toolbox**: an attack's effect is an ordered list of `EffectOp` structs (data, not bespoke per-card code), locked by `docs/superpowers/specs/2026-07-13-effect-engine-slice-1-design.md` on `feat/draft-mode-flow`. Slice 1 is already scoped there: 6 verbs across Sneasel, Petilil, Ponyta, Indeedee ex, Munchlax. Never propose per-card effect code or a per-ID effect map. **The opponent is a stand-in for a second human drafter**, not a bot design: P2's deck must come from an independent draft over the same pool under the same ruleset — a different selection, not a different process. The current hardcoded preset and any "random legal 20" are testing shims, never the target. Real opponents (and later ELO/MMR matchmaking) replace the stand-in; do not propose work that entrenches it.
**Done when:** I open the live site, draft a deck, play a run against a bot drafted from the same pool where cards do what their text says, and my run record persists.

## knowflow
**Is:** Service-desk tool turning KB text into editable, accessible preset diagrams.
**Stands:** Live on Vercel + Supabase, zero open PRs; code and flow content deploy on separate tracks — merging never updates flows, only `npm run seed:flows -- --force` does.
**Wants:** Actively being worked on. The immediate need is the user's own: editing flows against the real production app, which no automated run can do for them.
**Done when:** A teammate opens the live URL, reads an official flow without a password, and I edit one after unlocking.

## priority-post
**Is:** Personal smart to-do app with an AI planner.
**Stands:** Live on Vercel; `phase-3-discord-planner` is built and green but never merged, pending manual go-live wiring (Discord app, Vercel secret, Neon migration, Railway deploy); a second branch `planner-eval` is also unmerged.
**Wants:** **The highest priority of any project here.** Wanted in its final form as soon as possible. It is technically usable today and still not used — the missing pieces are what would make it genuinely worth opening every day.
**Done when:** I message the Discord bot, it plans my real tasks, and the plan appears in the live app.

## TTunes
**Is:** Personal always-on music station — curated library, 24/7 shuffle, AI fetches requested tracks.
**Stands:** `README.md` states "brainstorming/design phase"; TypeScript, last pushed 2026-07-14. No shipped surface.
**Wants:** Wanted, and wanted small: the simplest version that actually runs, as soon as possible. Prefer a thin working slice over more design.
**Done when:** Music plays continuously from my own library without me touching it.

## thomas-tahk-portfolio-game
**Is:** Interactive 2D portfolio site — visitors explore About/Skills/Experience/Projects by moving a character (React 19 + Vite + Kaplay + Jotai, per `README.md`).
**Stands:** Live on GitHub Pages; character movement is reported broken on the deployed site while working locally. Last pushed 2026-05-23.
**Wants:** Needs significant work before it can serve as the user's actual portfolio — not a demo, the real thing they point employers at.
**Done when:** A stranger opens the live Pages URL on desktop and phone, moves the character with WASD and touch, and opens the Projects modal.

## llm-plays-sc
**Is:** An LLM acting as strategist over a hand-coded execution layer to play StarCraft: Brood War (Java/Kotlin JBWAPI bot, Python strategist, JSON-over-socket IPC).
**Stands:** Design only — no bot code exists. `CLAUDE.md` names the single open spike: JBWAPI hello-world on Windows then Linux (ADR-0006), runbook at `docs/setup/windows-spike-runbook.md`.
**Wants:** Genuinely interesting to the user, but the scope as designed is bigger than they want. Prefer proposals that cut it down; do not propose work that widens it.
**Done when:** A worker mines and a building constructs under our control in a live StarCraft game.

## shows-for-us
**Is:** Full-stack app for tracking traveling musical performances and cast members in the US (React + Vite + TS, Express, Supabase, Ticketmaster API).
**Stands:** README describes the feature set as intent; last pushed 2026-04-13. No evidence in the repo of a deployed URL.
**Wants:** Definitely being picked up again.
**Done when:** not yet stated.

## amugonna
**Is:** Ingredient-first recipe app — turns what is actually in your fridge into meal recommendations, respecting dietary limits.
**Stands:** README still carries `placeholder-for-demo.gif` and "Live demo coming soon"; last pushed 2026-04-13.
**Wants:** Eager to resume. The user knows roughly where they want it to go but not where it currently is — orientation first: what exists, what runs, what is half-done.
**Done when:** not yet stated.

## ez-golf
**Is:** Golf tracking app that analyses performance patterns to name the 2–3 skills holding a round back and suggest drills; built in an Albuquerque GDG workshop.
**Stands:** README's demo link is still the literal placeholder `your-deployed-url-here`; last pushed 2025-09-09.
**Wants:** Open to refining it into something golfers would actually use, but low priority. It was a one-shot build and is treated as one.
**Done when:** not yet stated.

## pwp-rts-timeline
**Is:** A brief introduction to real-time-strategy video games, written from the perspective of someone who grew up with the genre.
**Stands:** Frontend-only HTML/CSS/Tailwind; README states an intended refactor to Astro + React that has not happened. Last pushed 2025-08-19.
**Wants:** **Retired — the user will not pick this up again.** An attempted Astro refactor went badly enough that they abandoned the project. Propose nothing here. The spirit of it continues in esports-tldr.
**Done when:** not yet stated.

## esports-tldr
**Is:** All-in-one short preview/summary of recent esports events across multiple titles; explicitly "a project for fun".
**Stands:** README's Installation and Usage sections both read "WIP"; scope deliberately cut to one game and one API. Last pushed 2025-05-18.
**Wants:** Interesting, but the scope needs discussion before any work is worth proposing. Hold: raise no work here until the user has settled what it should be.
**Done when:** not yet stated.
