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
**Stands:** `feat/draft-mode-flow` is 21 commits ahead of `main` and contains all of PR #1; the draft → deckbuild → play loop runs end to end locally, but the opponent still plays a hardcoded preset (`server/carddata.go:185-190`) and no card effects exist (`engine/types.go:63` — "Vanilla cards have only this — no special text").
**Done-gate:** I open the live site, draft a deck, play a run against a bot drafted from the same pool where cards do what their text says, and my run record persists.

## knowflow
**Is:** Service-desk tool turning KB text into editable, accessible preset diagrams.
**Stands:** Live on Vercel + Supabase, zero open PRs; code and flow content deploy on separate tracks — merging never updates flows, only `npm run seed:flows -- --force` does.
**Done-gate:** A teammate opens the live URL, reads an official flow without a password, and I edit one after unlocking.

## priority-post
**Is:** Personal smart to-do app with an AI planner.
**Stands:** Live on Vercel; `phase-3-discord-planner` is built and green but never merged, pending manual go-live wiring (Discord app, Vercel secret, Neon migration, Railway deploy); a second branch `planner-eval` is also unmerged.
**Done-gate:** I message the Discord bot, it plans my real tasks, and the plan appears in the live app.

## TTunes
**Is:** Personal always-on music station — curated library, 24/7 shuffle, AI fetches requested tracks.
**Stands:** `README.md` states "brainstorming/design phase"; TypeScript, last pushed 2026-07-14. No shipped surface.
**Done-gate:** not yet stated.

## thomas-tahk-portfolio-game
**Is:** Interactive 2D portfolio site — visitors explore About/Skills/Experience/Projects by moving a character (React 19 + Vite + Kaplay + Jotai, per `README.md`).
**Stands:** Live on GitHub Pages; character movement is reported broken on the deployed site while working locally. Last pushed 2026-05-23.
**Done-gate:** A stranger opens the live Pages URL on desktop and phone, moves the character with WASD and touch, and opens the Projects modal.

## llm-plays-sc
**Is:** An LLM acting as strategist over a hand-coded execution layer to play StarCraft: Brood War (Java/Kotlin JBWAPI bot, Python strategist, JSON-over-socket IPC).
**Stands:** Design only — no bot code exists. `CLAUDE.md` names the single open spike: JBWAPI hello-world on Windows then Linux (ADR-0006), runbook at `docs/setup/windows-spike-runbook.md`.
**Done-gate:** A worker mines and a building constructs under our control in a live StarCraft game.

## shows-for-us
**Is:** Full-stack app for tracking traveling musical performances and cast members in the US (React + Vite + TS, Express, Supabase, Ticketmaster API).
**Stands:** README describes the feature set as intent; last pushed 2026-04-13. No evidence in the repo of a deployed URL.
**Done-gate:** not yet stated.

## amugonna
**Is:** Ingredient-first recipe app — turns what is actually in your fridge into meal recommendations, respecting dietary limits.
**Stands:** README still carries `placeholder-for-demo.gif` and "Live demo coming soon"; last pushed 2026-04-13.
**Done-gate:** not yet stated.

## ai-advisor
**Is:** not yet characterised — repo description is "a template"; README is the unmodified `create-next-app` boilerplate.
**Stands:** No project-specific content committed. Last pushed 2026-04-01.
**Done-gate:** not yet stated.

## ez-golf
**Is:** Golf tracking app that analyses performance patterns to name the 2–3 skills holding a round back and suggest drills; built in an Albuquerque GDG workshop.
**Stands:** README's demo link is still the literal placeholder `your-deployed-url-here`; last pushed 2025-09-09.
**Done-gate:** not yet stated.

## pwp-rts-timeline
**Is:** A brief introduction to real-time-strategy video games, written from the perspective of someone who grew up with the genre.
**Stands:** Frontend-only HTML/CSS/Tailwind; README states an intended refactor to Astro + React that has not happened. Last pushed 2025-08-19.
**Done-gate:** not yet stated.

## esports-tldr
**Is:** All-in-one short preview/summary of recent esports events across multiple titles; explicitly "a project for fun".
**Stands:** README's Installation and Usage sections both read "WIP"; scope deliberately cut to one game and one API. Last pushed 2025-05-18.
**Done-gate:** not yet stated.
