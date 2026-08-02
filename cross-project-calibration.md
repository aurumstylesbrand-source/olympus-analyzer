# Cross-Project Calibration — 6 Accepted Olympus/Mars Projects

*Distilled from `/Users/mac/Desktop/olympus-experience/` + each project's source-of-truth local log, adversarially audited (2 clean, 4 minor_issues; all statuses confirmed, zero fabrications). Generated 2026-06-27. Full report: `experience-intelligence-extraction.md`.*

## The accepted board (calibration anchors)

| Project | Lang | Pass rate | Solver MSGs | LOC | Files | Desc words | Difficulty archetype |
|---|---|:--:|---|:--:|:--:|:--:|---|
| mangum (lambda streaming) | Py | 9% (1/11) | Orion 111 (sole); Nova 0/10 @ 55 (47–79) | 696 solver / ~542–554 patch | 9 / 13 | 500 | discovery gap (two-phase asyncio) |
| trpc (context factories) | TS | 20% (2/10) | Nova 133 (93–153); Orion never solved | 1380 | 17 | 499 | discovery gap (7 divergent adapters + silent invariants) |
| drizzle-keyset | TS | **RQB ver. UNMEASURED**; select-builder 60/100/80/60/100 | Nova 144 (53–153); Orion not run | 902 | 19 | 496 | discovery gap (unfamiliar RQB sibling path) |
| drizzle-chunked | TS | 20% (2/10); 75->60->20 | Nova 131.5 (117–154); Orion not run | 744 add / 959 | 15 | 500 | discovery gap x2 layers (seek, then non-unique PK auto-tiebreak) |
| drizzle-relation-agg | TS | **0/12 -> 3/5 -> dialed back (final UNRECORDED)** | Nova 124 (83–136); Orion best 44/45 | 718 | 29 | 490 | prerequisite bug-fix (driver JSON.parse corruption) |
| gorm-keyset | Go | 9% (1/11) cross-run; local 1/4=25% | Orion 124 (sole); Nova 0/~10 @ 36 local | 1208 / 1511 solver | 11 | 493 | breadth (19 test groups, no single gotcha) |

**The envelope every accept landed in:** 400–1380 LOC, 9–29 files, **490–500-word ASCII behavioral description**, >=1 solver with a hard ceiling.

## The two proven difficulty archetypes

1. **Discovery gap** — an unfamiliar code path or a non-guessable invariant agents get wrong *by default*. (trpc adapters, drizzle RQB, chunked PK-tiebreak, relation-agg JSON corruption.)
2. **Breadth** — a legitimately broad public API where correct *composition* across many groups holds the rate down with no single trick. (gorm 19 groups, mangum.)

**Edge-case volume on a known surface NEVER moved a pass rate** (proven on drizzle-keyset & -chunked). A known algorithm needs **as many discovery layers as it has derivable simplifications** — count them before building, budget 2 batches.

## Top recurring checks (codify pre-submit gates for these)

- **Plagiarism = GATE ZERO** — 3 of 6 forced a pivot (mangum 0.615, trpc 0.835, gorm 0.872), all same-repo, all checked too late.
- **Test Fairness** (5–6/6): never pin author/impl choices (exact strings, split counts, SQL text, start order).
- **Solution Quality** (5/6): grades the public/type surface + portability + composition lifecycle, not passing tests. "Composes with X" = audit X's FULL framework lifecycle in ONE pass (gorm burned 4 rounds).
- **Verify-Solution/F2P** (4/6): guard tests pass without the solution — lead each with `typeof method === 'function'` + a positive canary; never bare `.toThrow()`.
- **Description/Aligned** (5/6): name WHAT not HOW. Name signatures for fairness (gorm had to ADD them; trpc broke when it REMOVED them) but never over-spec internals/mechanism. Pure ASCII (em-dash is the AI tell).

## Nova behavior (stable across all 6)

- Nova **derives any known algorithm correctly and fast**; **fails fast on transparent APIs** (47–79 msgs). Accept **Orion-only solves** as a valid Hard equilibrium, not a calibration failure.
- **NO file records a time-based Nova "amping" series.** Every "trend" is design-driven (levers added between batches) or pre-batch estimate. The CLAUDE.md "AMPED Nova" recalibration is external context, unproven here.
- **Read solver patches between every batch** — one grep ("0/10 used a tiebreaker") pinpoints the exact next lever.

## Corrections to prior beliefs / data hygiene

- **Stop using `<=30%` for Olympus.** 3 logs (keyset, relation-agg, gorm) judged PASS against the Mars `<=30%` cap; under the Olympus `<=20%` bar several are borderline. Recalibrate any reuse.
- **trpc source-internal errors:** agent-LOC median is 1231.5 (logged 1367.5); files median 15 (logged 16.5); Nova range 93–153 (the 88 was a different batch).
- **Two "accepted" rates are not real measurements:** drizzle-keyset RQB (never batched) and relation-agg final (dial-back unrecorded). gorm "9%" is a cross-run figure; only a 1/4=25% local batch is itemized.

## Repo env playbooks (the traps that cost batches)

- **drizzle-orm:** RQB is the Olympus must-have (select-builder alone never cleared the bar); SingleStore RQB is stubbed; proxy-to-sqlite can't run dialect JSON aggregation; PGlite WASM OOMs ~8.9GB locally (trust Docker); strip the self-ref drizzle-kit prerelease from package.json + all 3 lockfile locations then `--frozen-lockfile`; every new src dir referenced by the root barrel needs an index.ts; new src files get auto-discovered by `exports.test.ts` (skip via base config `test.exclude`, not the fragile `--exclude` CLI).
- **gorm:** content-based stub detection (`grep 'type Page'`), stub in `_test.go` in package gorm; PK tiebreaker on the forward ORDER BY SQL (SQLite masks a missing ORDER BY via insertion order); `Statement.clone()` to avoid PageIter infinite loop.
- **trpc:** core code in `src/contextFactory/` NOT `adapters/`; bare `node:` imports + default CJS imports break in platform vitest; repo-relative patch headers only.
- **mangum:** centralize exceptions in `mangum.exceptions` (submodule exception broke an all-or-nothing import guard, errored 42 tests); `.venv/bin/pytest` not `uv run`.
