# OLYMPUS EXPERIENCE INTELLIGENCE EXTRACTION

*Generated 2026-06-27. Source: every file in `/Users/mac/Desktop/olympus-experience/` plus each project's source-of-truth local log (mangum/, trpc/_artifacts/, drizzle-orm/, drizzle-orm2/_artifacts/, drizzle-orm4/_artifacts/, grom4/). Each extraction was adversarially audited against its sources; corrections are folded in and flagged.*

**Method note:** 6 per-project extractions were produced by per-file agents reading the centralized summary + the local chronological log, then each was checked by an adversarial honesty auditor. Audit verdicts: **2 clean** (relation-aggregations, gorm-keyset), **4 minor_issues** (mangum, trpc, drizzle-keyset, drizzle-chunked) — all status confirmations TRUE, zero fabrications. Where a datum is not in the files, it says **"not recorded."**

## Three load-bearing honesty caveats (affect how to trust the pass-rate numbers)

1. **Two "accepted" projects have NO measured final pass rate.** drizzle-keyset's accepted RQB version was never agent-batched (the `<=30%` is a *prediction*; last real batch was 100%). drizzle-relation-aggregations' final was `0/12 -> 3/5 -> "dialed back"` — the dial-back batch's result was **never recorded**.
2. **gorm's "9% (1/11)" is a cross-run figure** whose 11-run denominator is itemized nowhere; the only detailed local batch was `1/4 = 25%`.
3. **The pass-rate CAP is inconsistent across the files.** Several logs (drizzle-keyset, drizzle-relation-agg, gorm) use the **Mars `<=30%`** cap even though they are Olympus projects — they predate / don't reflect the global **Olympus `<=20%`** rule. Treat their "PASS at <=30%" verdicts with that lens.

---

## SECTION 1: INVENTORY

| File | Repo | Feature | Status | Language |
|------|------|---------|:------:|----------|
| `README.md` | — | Index / GATE-ZERO reminder | reference doc | — |
| `accepted-problems-debrief.md` | — | Consolidated calibration table (Problems 1–4) + 13 cross-problem principles | reference doc | — |
| `lambda-response-streaming-mangum-exp.md` | Kludex/mangum | Lambda response streaming for ASGI (eager prelude + lazy backpressured body) | **ACCEPTED** 2026-06-02 | Python |
| `context-factories-trpc-exp.md` | trpc/trpc | Request-scoped context factories w/ lifecycle hooks across 7 adapters | **ACCEPTED** 2026-06-10 | TypeScript |
| `drizzle-orm_keyset-pagination_exp.md` | drizzle-team/drizzle-orm | `.paginate()` keyset pagination, 4 dialects + RQB | **ACCEPTED** 2026-06-18 | TypeScript |
| `drizzle-orm_chunked-iteration_exp.md` | drizzle-team/drizzle-orm | `.chunked(size)` stable batched iteration, 4 dialects + RQB | **ACCEPTED** 2026-06-24 | TypeScript |
| `drizzle-orm_relation-aggregations_exp.md` | drizzle-team/drizzle-orm | RQB relation aggregations + prerequisite JSON-precision codec | **ACCEPTED** 2026-06-26 | TypeScript |
| `gorm_keyset-pagination_exp.md` | go-gorm/gorm | Bidirectional keyset pagination on `*gorm.DB` | **ACCEPTED** 2026-06-27 | Go |

**6 accepted projects, 0 rejected/pending in this folder.** (Rejected/abandoned *ideas* live *inside* the accepted logs as pivots — Section 6.) One status nuance: drizzle-keyset's **local** log header still reads `VALIDATING` (never updated); acceptance is confirmed by the centralized summary + REPO_INTELLIGENCE (Marouane Chemrah 6/7, Leonard Tng final, 21/21).

---

## SECTION 2: WHAT MADE EACH ACCEPTED PROJECT SUCCEED

| Project | Pass Rate | MSGs (solver) | LOC | Files | What Created The Difficulty | Fix Iterations |
|---|:--:|:--:|:--:|:--:|---|:--:|
| **mangum** | 9% (1/11) | **Orion 111** (sole solver); Nova 0/10, median 55 (47–79) | 696 solver / ~542–554 ref-patch added | 9 solver / 13 patch (10 new+3 mod) | Two-phase asyncio contract: must return at `http.response.start` (eager prelude) then stream body lazily w/ backpressure — "lazy" splits agents into all-lazy vs all-eager, both wrong | 22 phases (16 root_path + 6 streaming); 67 lessons |
| **trpc** | 20% (2/10) | Nova median **133** (range **93–153**, audit-corrected from 88); Orion **never solved** (164/175/176 all FAIL) | 1380 patch | 17 (7 new + 10 mod) | 7 shipped adapters each w/ a *different* existing createContext pattern + >=5 silently-failing cross-cutting invariants (phase placement, Promise.allSettled rollback, shared cleanup-promise) | 48 FIXes (12 policyGuard + pivot #13 + 35 contextFactory); 4 batches |
| **drizzle-keyset** | Select-builder **never** hit <=30% (chronological **60/100/80/60/100**); **final RQB version NOT measured** | Nova median **144** (53–153); Orion not run | 902 | 19 | Keyset is a *known* algorithm; accept-grade gap = wiring into the **unfamiliar RQB sibling path** (callback orderBy/where, JSON aggregation, nested rows) | 10 FIXes + 5 batches |
| **drizzle-chunked** | 20% (2/10) final; trajectory **75->60->20** | Nova median **131.5** (117–154, below 150 floor); Orion not run | 744 added / 959 patch | 15 | Known algo + **TWO** discovery layers: offset->seek (stability under deletion), then **non-unique column forcing compound PK auto-tiebreak** (`getTableColumns`) | 14 FIXes + 3 batches |
| **drizzle-relation-agg** | **0/12 -> 3/5 (60%) -> "dialed back"** (final not recorded) | Nova solver 124 (83–136); Orion best rollout 44/45 | 718 | 29 | Feature secretly **requires a prerequisite bug-fix codec** (driver `JSON.parse` corrupts numeric/bigint before drizzle decodes) spanning column-types + RQB + dialects | 7 FIXes |
| **gorm-keyset** | 9% (1/11) cross-run; local batch 1/4=25% | **Orion 124** (sole solver); Nova 0/~10, local median 36 | 1208 patch / 1511 solver median | 11 (agent median 3) | **Breadth-as-difficulty**: 19 test groups / 81 tests of correct-composition behavior, no single gotcha; built ABOVE gorm's helper layer | 10 FIXes + 10 reviewer Rounds |

**The shared shape:** every accepted project landed **400–1380 LOC**, **9–29 files**, **descriptions 490–500 words**, and **>=1 solver** (Orion-only for mangum & gorm; Nova-only solves for the drizzle pair; both for trpc). Two distinct equilibria recur: **"Orion-solves / Nova-fails-fast"** (mangum, gorm — transparent or broad API) and **"Nova-solves-slowly near the floor"** (trpc, drizzle).

---

## SECTION 3: NOVA BEHAVIORAL PATTERNS

| Project | What Nova Got RIGHT | What Nova Got WRONG | MSGs Pattern | Evidence |
|---|---|---|:--:|---|
| **mangum** | Built the correct file/module layout (spec-readable surface) | **All 10 failed on one root cause**: didn't drive app to `http.response.start` before return. Cluster A (7/10) fully-lazy; Cluster B (3/10) fully-eager. None found the middle | median **55** (47–79), fails fast & cheap | summary L88–92, L46 |
| **trpc** | The 2 PASS Novas put `phase` as top-level onError field, async-wrapped create->allSettled, spent ~40% budget on test-fix cycles | A 92-step Nova put `contextFactory.ts` in `adapters/` not core -> every adapter cascaded; BATCH#3 all 7 guessed hook signatures wrong | median **133**, range 93–153 | centralized L116–121 |
| **drizzle-keyset** | Derived *every* keyset edge case from training (seek, limit+1, backward flip, NULLS LAST, even backward-null-flip independently) | The `normalizeOrderBy` field-resolution wall (parsing `asc(col)` back to column) — all 4 Batch#4 fails same reason | 77->103->135->144; pass rate immovably high | exp L428–430, L490 |
| **drizzle-chunked** | After seek pivot, worked genuinely (117–154 band); 2 final solvers built compound PK-tiebreak | BATCH#2 **all 6** wrote naive `gt(col,last)` w/ NO tiebreaker, passed only because tests ordered by a UNIQUE id (~0 use of getTableColumns) | 47/85/152 -> median 131.5 | local L532–536 |
| **drizzle-relation-agg** | Post-hints 3/5 solved at 124/83/136, depth was fine (18 files, 403 LOC) | Pre-hints 0/12. Three blind spots: numeric[] element-wise recursion (11/12), per-op decimal-string decode (10), subquery-as-table aliasing (5) | 0/12 -> 3/5 after 2 hints | local L176, L199 |
| **gorm-keyset** | One Nova solved clean 947-LOC / 2-file impl in 36 msgs | In the recorded batch Nova mostly **bailed on env/compile cascade** (stub redeclaration, counter field-vs-method), not behavior; behavioral killers (filtered-pagination timeout, Scope ORDER BY) hit the broader run | local median **36** (LOW — bailed on compile, not difficulty) | local L612, L615–622 |

### Trend analysis — has Nova changed over time?

| Time Period | Nova Behavior Observed | Evidence |
|---|---|---|
| Across all 6 projects (Jun 2–27 2026) | **No file records a genuine time-based Nova "amping" / speed series.** Every "trend" is either (a) *design-driven* — behavior changed because levers were added between batches, not because Nova got faster — or (b) *pre-batch estimates*, not measured solves | mangum/drizzle-chunked/gorm nova_trend (all explicitly "design-driven, not time-based"); relation-agg "behavior changed only as a function of hint changes, not time" |
| Consistent finding | **Known-algorithm features -> Nova derives them correctly and fast** (keyset/chunked/offset are transcribable from training). Difficulty must come from an *unfamiliar code path* or *non-guessable invariant*, never edge-case volume | drizzle-keyset (two Novas independently coded the exact backward-null lever just added); drizzle-chunked (0/10 used a tiebreaker) |

> **Direct answer to "did the platform update agents / did Nova get better over time?"** — **Not recorded in these files.** The global CLAUDE.md "AMPED Nova (May 2026)" recalibration is *external context*; none of the six logs contains a measured baseline-vs-amped comparison. What they *do* show is that Nova's ceiling is set by **structural transparency**, and that is stable across all six.

---

## SECTION 4: DIFFICULTY MECHANISMS THAT WORKED

| Project | Difficulty Mechanism | Pass Rate Achieved | Generalizes To Other Repos? |
|---|---|:--:|:--:|
| **mangum** | Two-phase asyncio contract; single word "lazy" bifurcates agents; discriminating tests fail *both* extremes | 9% | **Yes** (file says broadly applicable to any streaming/pipeline feature); expect Orion-only solves |
| **trpc** | Wire into **5+ existing code paths with different patterns** + >=2 silently-failing cross-cutting invariants ("the Path A signature") | 20% | **Yes, explicitly** — "for repos with multiple parallel adapter/driver/backend implementations" |
| **drizzle-keyset** | Expand a known algorithm into an **unfamiliar sibling code path** (RQB) that can't be pattern-matched | (RQB version unmeasured) | Partial — stated reusable for *drizzle* specifically; principle (sibling path) generalizes |
| **drizzle-chunked** | **Count derivable simplifications and strip each**: offset->seek, then unique->non-unique PK auto-discovery (2 layers) | 20% | Partial — RQB is the drizzle structural must-have; the "count the layers" principle generalizes |
| **drizzle-relation-agg** | **A feature that requires a prerequisite bug-fix** whose root cause lives *outside the repo* (driver JSON.parse); "named-but-not-mechanized" hints | 60% (then dialed back, final unrecorded) | Shape generalizes (coherent cross-subsystem); repo-portability **not recorded** |
| **gorm-keyset** | **Breadth-as-difficulty**: 19 behavioral groups of correct-composition, no single trick, built above the helper layer | 9% | **Yes** — "reliably holds 9–20% when the feature genuinely has that surface area"; don't manufacture breadth, recognize it |

**The two proven difficulty archetypes:** (1) **Discovery gap** — an unfamiliar code path or non-guessable invariant agents get wrong *by default* (trpc, both drizzle keyset/chunked, relation-agg). (2) **Breadth** — a legitimately broad API where correct composition across many groups holds the rate down (gorm, mangum). **Edge-case volume on a known surface never moved a single pass rate** (proven on drizzle-keyset and -chunked).

---

## SECTION 5: CHECK ITERATION PATTERNS

| Project | Top Checks That Failed Most | Total Iterations | What Caused Most Iterations |
|---|---|:--:|---|
| **mangum** | Plagiarism (root_path 0.615) -> full pivot; Test Fairness (P4/7/20/22); Description Quality; Solution Quality (buffered-not-streaming) | 22 phases / 67 lessons | The **plagiarism gate** (scrapped 16 phases); then the Solution-Quality "looks-streaming-internals-buffered" rewrite |
| **trpc** | **Tests-Cover (6) tied Aligned (6)**; Solution Quality (#25,#26); Description Quality (3x); Test Fairness | 48 FIXes / 4 batches | The 3-way **Description-Quality <-> Aligned <-> Test-Fairness tension** on the same clauses; worst single event = FIX#40 voice-rewrite stripping signatures -> 0/7 |
| **drizzle-keyset** | **Pass-rate/difficulty too-easy (5x)**; Solution Quality (3x: non-portable SQL, missing barrel, deleted success test); Test Fairness (3x) | 10 FIXes + 5 batches (~16 pre / 6 post) | **Being too easy** — known algorithm, no discovery gap until the RQB expansion (FIX#8) |
| **drizzle-chunked** | Pass-rate/difficulty (3 batches); Verify-Solution/F2P traps; Env/Docker/PGlite; Description/Aligned | 14 FIXes + 3 batches | **Pass-rate** — one discovery layer insufficient; took 3 batches to land both layers |
| **drizzle-relation-agg** | **Difficulty calibration (2x: too-hard then too-easy)**; Verify-Solution F2P; Solution Quality (4 real bugs); Test Fairness; cross-dialect Alignment | 7 FIXes | **Hint-sensitivity** — 2 phrases swung 0%->60% |
| **gorm-keyset** | **Reviewer "Meets all requirements"/Solution Quality (4 Rounds)**; Test Fairness (repeated); Description Quality; Agent-runs UNFAIR (stub cascade) | 10 FIXes + 10 Rounds | **4 separate Solution-Quality rounds on sibling "composes with X" gaps** (NULLS, sql.NullString, Scopes, DecodeCursorMeta) — "could have been one audit" |

### Cross-project: which checks fail on (almost) every project?

| Check | Failed On | Root-Cause Pattern |
|---|:--:|---|
| **Test Fairness** | 5–6 of 6 | Pinning author/implementation choices not in the description (exact strings, split counts, SQL text, start-order, TS ergonomics) |
| **Solution Quality** | 5 of 6 | Grades the **public/type surface + portability + composition lifecycle**, not just passing tests (non-portable SQL, missing barrel, buffered internals, half-honored "composes with X") |
| **Description Quality / Aligned** | 5 of 6 | Over-specification of internals/mechanism; the eternal "state behavior" vs "don't over-spec" vs "tests pin it" tension; em-dash/ASCII rejections |
| **Pass-rate / difficulty calibration** | 4 of 6 (all the "too-easy" side) | Known algorithm -> too easy; required a discovery gap, not more tests |
| **Plagiarism (GATE ZERO)** | 3 of 6 forced a pivot | mangum 0.615, trpc-offline 0.835, gorm-optimistic 0.872 — all same-repo, checked too late |
| **Verify-Solution / F2P** | 4 of 6 | Tests pass WITHOUT the solution (bare `.toThrow()`, "X is exported", guard-without-canary) |
| **Env / Docker / test.sh** | 4 of 6 | Lockfile/prerelease, PGlite OOM, `--no-frozen-lockfile` rejected, absolute patch paths, exec bit, test-file collisions |

---

## SECTION 6: WHAT MADE PROJECTS (sub-ideas) FAIL OR GET ABANDONED

No project in the folder was rejected. But each accepted log records **abandoned ideas / pivots** — this is the real "what fails" data:

| Project | Abandoned/Failed Idea | Why | Could It Have Been Saved? | Lesson |
|---|---|---|:--:|---|
| **mangum** | Comprehensive `root_path` support | **Plagiarism 0.615 same-repo** (matched Kludex/mangum's own raw-path work) | No — same core idea = DEAD | Plagiarism FIRST; 16 phases wasted |
| **mangum** | Internal-module unit tests (importing `parse_forwarded` etc.) | Prescribed implementation; not public-interface | Yes (test the handler API) | Behavioral tests on public surface only |
| **mangum** | Buffered-internals "streaming" | Solution Quality: surface looks streaming, internals buffered | Yes (true lazy body) | Return BEFORE the app finishes |
| **mangum** | Handler-only solution scope | Task Quality 08 — single-subsystem = Mars-tier | Yes (span config+adapter+handler) | Olympus needs cross-subsystem |
| **trpc** | `createTRPCPolicyGuard` (ABAC) | Structural ceiling: 13 iters stuck ~80% / 63-msg solves; API too small | No — pivot at FIX#13 | Same-shape + low-msg + bot-contradiction >=3 batches = too small, pivot |
| **trpc** | `createOfflineTRPCClient` | **Plagiarism 0.835 same-repo** | No | A replay/cache helper has unavoidable same-repo overlap |
| **trpc** | FIX#40 voice-rewrite to "human prose" | Silently **stripped function signatures** -> BATCH#3 0/7 | Yes (FIX#47 re-added signatures) | Name the signature in prose even when conversational |
| **drizzle-keyset** | `IS NOT DISTINCT FROM` seek predicate | Postgres-only, non-portable | Yes (branch on isNull) | Portable SQL across all 4 dialects |
| **drizzle-keyset** | More same-scope edge-case tests | Thorough Novas pre-empt breadth | No | Breadth isn't a lever vs thorough agents |
| **drizzle-chunked** | setMany / window-fns / relation-aggregates as the *feature* | Naturally too small (210/261/159 LOC) — SQL-only, shared helper collapses LOC | No (wrong feature shape) | Need new method + new result shape + non-collapsing per-dialect execution |
| **drizzle-chunked** | Stateless SQL-parsing proxy | Can't parse parameterized `limit ?`; baked in offset assumption | Yes (stateful proxy w/ explicit batchSize) | Never regex LIMIT/OFFSET from drizzle SQL |
| **relation-agg** | Bug-fix-only problem (123 LOC) | Below 700 LOC floor; a fix removes lines | Yes — **find the feature the fix unlocks** | Convert bounded fix into the prerequisite for a coherent feature |
| **relation-agg** | Claim all 5 dialects | Alignment ERROR — only pg+sqlite runtime-testable | Yes (narrow to pg+sqlite) | Describe only what tests verify |
| **gorm** | GORM Optimistic Locking | **Plagiarism 0.872 same-repo** | No | GATE ZERO (3rd strike: mangum, conf, gorm) |
| **gorm** | Stub in regular `.go` file; filename-based detection | Test-Patch-Sanity rejects impl files; probe lies on agent quirks -> redeclaration cascade | Yes (`_test.go` stub + content-based grep detection) | Content-based solution detection |
| **gorm** | Retrospective opener "This submission adds..." | A Nova read it as a PR review and never coded | Yes (imperative voice) | Lead "Add...", never retrospective tense |

---

## SECTION 7: DESCRIPTION TECHNIQUES

| Project | Word Count | Opener Style | What Passed Description Quality | What Got Flagged |
|---|:--:|---|---|---|
| **mangum** | **500** | Leads with target behavior, not background | Clean module separation praised; lazy-iteration tests "nail the part most agents got wrong" | Em-dash UTF-8 rejections; over-pinned tests (split count) |
| **trpc** | **499** | "Today X, add Y" ticket-style; names APIs in prose at point of use; **signatures in behavioral form** ("onCleanup(input, ctx) runs at the end (awaited)") | Holistic 25-PASS; "fair, difficult... ship as-is, no hints" | Over-spec of internals (`runContextLifecycle`, `Promise.all`), "should expose" spec-voice, em-dashes; FIX#40 over-corrected -> stripped signatures |
| **drizzle-keyset** | **496** | Plain declarative: "Add keyset pagination to the select builder across Postgres, MySQL, SQLite, SingleStore." | "Complete, self-contained, deterministic"; **style never flagged** | Only *fairness*-adjacent prose trimmed; led para 1 with drizzle differentiators to separate from the TypeORM `similar_idea` match |
| **drizzle-chunked** | **500** | **De-recipe'd** — leads with the stability invariant woven into prose, not an enumerated checklist | 0 non-ASCII; explicitly states ascending PK tie-break + findFirst-throws | findFirst contradiction (FIX#9); PK tie-break direction unstated (FIX#13) |
| **relation-agg** | **490** | **not recorded** (opener not quoted) | Task Quality 7/8; reviewer praised "fidelity work via column-level hooks" | 2 SQL-text fairness assertions; cross-dialect over-claim (5 vs pg+sqlite) |
| **gorm** | **493** | Imperative feature voice: "Add bidirectional keyset pagination on `*gorm.DB`..."; differentiator (no native backward walk) in first 1–2 sentences | Holistic PASS; "fair, very hard... ship as-is, no hint needed" | Over-spec of internals (`Statement.Settings`, clause internals); payload-shape pins; *and* Alignment flagged **missing** signatures that had to be ADDED |

**The description sweet spot (all 6):** **490–500 words**, behavioral verbs, pure ASCII (em-dash is the recurring AI tell), backticks only on identifiers tests actually pin, contracts integrated across sentences. **Tension to manage:** name signatures/return-types enough for fairness (gorm had to *add* them; trpc broke when it *removed* them) but never over-specify *mechanism/internals* (both got flagged for that). "Name WHAT, not HOW."

---

## SECTION 8: THE GENERALIZABLE PRINCIPLES

| Principle | Evidence (projects) | How To Apply Generally |
|---|---|---|
| **Plagiarism is GATE ZERO — check the CORE IDEA on the same repo before writing any file** | mangum 0.615, trpc 0.835, gorm 0.872 (3 forced pivots) | 5-min grep + queue + tool check *before* implementation; a duplicate central idea is DEAD, a rewrite never saves it |
| **Difficulty = a discovery gap, NOT test volume** | drizzle-keyset & -chunked (edge cases never moved the rate); trpc | Pick something agents must *discover* (unfamiliar code path / non-guessable invariant), not just implement |
| **A known algorithm needs as many discovery layers as it has derivable simplifications** | drizzle-chunked (offset->seek lifted MSGs but only 75->60%; needed non-unique+PK as layer 2) | Before building, list every simplification agents will reach for and a lever to strip each; budget 2 batches |
| **Wire into 5+ different-pattern code paths + >=2 silently-failing cross-cutting invariants** | trpc (7 adapters); the "Path A signature" | On any multi-adapter/driver/backend repo, this locks a 100+ MSG exploration floor |
| **"Composes with X" is a full-lifecycle contract** | gorm (Scopes that add ORDER BY must be read AFTER executeScopes — 4 wasted rounds) | Audit EVERY composition claim against the framework's execution order in ONE pass |
| **Never delete a success-path test to fix fairness** | drizzle-keyset (platform re-synthesizes & fails it) | Replace with a fair fixture or convert to "declared-behavior-survives" assertion |
| **Every guard/negative test needs a positive canary; bare `.toThrow()` / "is exported" pass without the solution** | drizzle-chunked, relation-agg, trpc | Lead each guard with `expect(typeof method).toBe('function')` + a positive precision canary |
| **The UNFAIR-fix trap: fixing one unfair test spikes pass rate** | trpc, mangum | In the SAME submission, pair the clarification with 2–3 hard tests — UNLESS you're *documenting* (not removing), which leaves difficulty unchanged |
| **Two-reviewer fairness meta-trap** | gorm | If a fairness flag hits a test a prior reviewer requested, DOCUMENT the behavior, never remove it; grep the reviewer log first |
| **Solution Quality grades the public/type surface + portability, not passing tests** | trpc (types), drizzle-keyset (portable SQL + barrels), chunked (real per-dialect execution) | Don't collapse per-dialect execution into one shared helper (kills both LOC and the grade) |
| **Description: 490–500 words, name WHAT not HOW, pure ASCII** | all 6 | Name signatures for fairness; never over-spec internals/mechanism |
| **Read solver patches between every batch** | drizzle-chunked ("0/10 used a tiebreaker" -> exact next lever) | One grep beats guessing; it pinpoints the next discovery layer |
| **Prove a hard test DISCRIMINATES** | drizzle-chunked, relation-agg | Neuter the helper to the naive impl and confirm the new tests FAIL against it |
| **Breadth-as-difficulty is a legitimate accepted equilibrium** | gorm (19 groups), mangum | When a feature *genuinely* has broad API, lean in; don't manufacture breadth |
| **When a bug-fix is too small for the LOC floor, build the feature it unlocks** | relation-agg (codec -> relation aggregations) | Turns a bounded ~120-LOC fix into a coherent 700+ cross-subsystem enhancement |

---

## SECTION 9: REPO-SPECIFIC INTELLIGENCE

| Repo | Dockerfile | test.sh Pattern | Package Placement | Gotchas | Unused Code Paths (available) |
|---|---|---|---|---|---|
| **mangum (Python)** | `olympus-base-python`, `--network none` safe; `uv sync --frozen` then `.venv/bin/pytest` (not `uv run`) | mode 100755 (preserve exec bit); `--output_path` + JUnit XML + base/new; `--continue-on-collection-errors`; build patch w/ `git -C /repo diff --no-index` (**relative** header) | New `mangum/streaming/` package; **exceptions MUST centralize in `mangum.exceptions`** (defining `PreludeError` in a submodule broke an Orion run's all-or-nothing import guard -> errored all 42 tests) | `LambdaConfig` TypedDict requires `api_gateway_base_path` (pass `{'...': None}` not `{}`); `strip_api_gateway_path` returns `''` not `/`; Lambda@Edge uses `cloudfront-forwarded-proto` + key `status`; re-raise `CancelledError`; `weakref.finalize` to avoid pytest hangs | (Removed dead `coalesce_below`/`ChunkBuffer`) |
| **trpc (TS)** | `olympus-base-typescript`; install `--ignore-scripts --no-frozen-lockfile`; vitest wrapper must be a **real script not a symlink** | Ships INSIDE test.patch w/ `new file mode 100755`, distinct base/new modes; **patch headers repo-relative** (absolute `--no-index` silently created `repo/Users/...` and the test never landed) | `packages/server/src/contextFactory/` (**CORE, not adapters/** — a Nova that put it in adapters/ cascaded every integration) | `node:` prefix imports fail in platform vitest (use bare); default CJS import -> undefined (use named); `rootConfig` widening cascades 33 TS errors; `ReadableStream` tap must use `pull()` not `start()`; brand via private WeakSet not forgeable prop | `next-app-dir`, `applyWSSHandler` return shape preserved |
| **drizzle-orm (TS)** — *keyset, chunked, relation-agg all share this repo @ 48e54060* | **Recorded verbatim** (keyset REPO_INTEL): `public.ecr.aws/d3j8x8q7/olympus-base-typescript:latest`, `pnpm install --no-frozen-lockfile`, then a `node -e require('better-sqlite3'/'@electric-sql/pglite')` warm-up. **BUT chunked corrected this**: strip the self-referencing drizzle-kit prerelease from package.json **AND all 3 pnpm-lock locations**, then use `--frozen-lockfile` (guidelines reject `--no-frozen-lockfile`) | At repo ROOT, mode 100755; base mode must **skip new src files** that `exports.test.ts` auto-discovers (chunked used `--testNamePattern '^(?!...)'`; relation-agg used a `vitest.base.config.ts` w/ `test.exclude` — **don't use the version-fragile `--exclude` CLI**); PGlite tests LAST | Shared core in new top-level `src/<feature>/index.ts` + per-dialect glue in each `src/<dialect>-core/query-builders/`; **every new dir referenced by root barrel MUST have index.ts** (missing barrel broke ALL baseline imports); hashed test filenames | **RQB is the Olympus structural must-have** (select-builder alone never cleared the bar); **proxy-to-sqlite can't run dialect-specific JSON aggregation**; **SingleStore RQB is stubbed** (`db.query = {}`); nested many-relation arrays unordered unless relation declares orderBy; **PGlite WASM JIT OOMs ~8.9GB locally regardless of NODE_OPTIONS — trust Docker**; driver `JSON.parse` corrupts numeric/bigint before decode | gel-core dialect (untouched), ~25 drivers, insert/update/delete + RETURNING, count/$count, transactions/savepoints, CTEs — all unused & available |
| **gorm (Go)** | High-level only: `olympus-base-go`, `WORKDIR /app`, `CMD bash`; `go-junit-report` installed. Full contents **not recorded** | `-run` regex (`^TestPaginat|^TestDecodeCursorMeta|...`); **content-based** solution detection (`grep 'type Page'` in non-test .go) to toggle `paginate_stub` build tag — *not* filename or compile-probe (those lie); JUnit exit status must propagate (remove `2>/dev/null || true`) | Main pkg `gorm` (pagination.go, cursor*.go, keyset.go, errors.go, paginate_iter.go) + sub-pkgs `clause/`, `schema/`, `callbacks/` = 11 files; **stub MUST be `_test.go` in package gorm** (visible to `gorm_test`); helper prefix `pag` to avoid agent collisions | `PageIter` reusing `clone=0` shares `Statement.Settings` -> infinite loop on 3rd call (use `Statement.clone()`); Select omitting sort col zeroes cursor (needs refetch); PK tiebreaker must be on the **forward ORDER BY SQL** not just cursor meta (SQLite masks missing ORDER BY via insertion order); `userSelectActive` must check both `stmt.Selects` and `stmt.Clauses['SELECT']` | Removed dead exports: `ErrPaginateExtractFailed`, `parseCursorTime`, `InjectPaginatePredicate`, `PrimaryKeyDBName`, `PageIter.WithDB` |

---

## SECTION 10: RECOMMENDATIONS

**1. Single most important lesson across all accepted projects.**
**Difficulty is a *discovery gap*, not test volume — and you must name that gap (and count its layers) BEFORE writing code.** Edge cases on a known surface never moved a pass rate in any of the six. The wins came from an unfamiliar code path (trpc adapters, drizzle RQB), a non-guessable invariant (chunked PK-tiebreak, relation-agg JSON corruption), or legitimate breadth (gorm, mangum).

**2. Pattern in EVERY successful project.**
Three things are present in all six: (a) **>=1 solver but a hard ceiling** (Olympus-tier difficulty held); (b) a **490–500-word, pure-ASCII, behavioral description** that names WHAT not HOW; (c) **multi-file, cross-subsystem work** (9–29 files) that Solution Quality grades on its *public/type surface and composition*, not just passing tests.

**3. Mistake in EVERY failed/abandoned idea.**
**Deferring the same-repo plagiarism check** (3 forced pivots) and **picking a feature that's structurally too small / collapses into a shared helper** (trpc policyGuard, the 3 abandoned drizzle features, the bug-fix-only relation-agg). The "fails" were always *wrong feature shape chosen too late*, never bad execution.

**4. What the prompt system should emphasize MORE.**
- **A pre-build "discovery-layer census"**: list every derivable simplification + a lever for each, and decide whether you're going for *discovery gap* or *breadth*. Budget 2 batches.
- **"Composes with X" = full-lifecycle audit in ONE pass** (gorm burned 4 rounds; the cost is real and repeated).
- **Read solver patches between batches** (one grep > guessing).
- **Verify-Solution/F2P discipline**: guard+canary, no bare `.toThrow()`, "prove it discriminates by neutering the helper."
- **Repo-level env playbooks** — the drizzle lockfile/PGlite and gorm stub-detection traps recurred and cost batches; codify them per repo.

**5. What the prompt system should STOP saying / fix.**
- **Stop using `<=30%` for Olympus projects.** Three of six logs (drizzle-keyset, relation-agg, gorm) judge "PASS" against the **Mars `<=30%`** cap, contradicting the global **Olympus `<=20%`** rule. Several "accepted at <=30%" verdicts would be *borderline-to-fail* under the tightened bar — recalibrate any reuse of those numbers.
- **Stop treating "AMPED Nova got faster over time" as observed here.** It's external; these files show **no measured time-trend**. Nova's behavior is set by *structural transparency*, not a date.
- **Stop quoting trpc's `1367.5` agent-LOC-median and `16.5` files-median** — those are **source-internal arithmetic errors** (true medians 1231.5 and 15 from its own per-run tables). And trpc's Nova range is **93–153** (the 88 was a different batch).

**6. Has Nova changed over time? How should strategy adapt?**
**Not measurable from these files** — no baseline-vs-amped series exists. What's *stable and reliable*: Nova **derives any known algorithm correctly and fast** and **fails fast on transparent APIs**. Strategy: never bet difficulty on edge cases against Nova; bet it on an unfamiliar code path, a non-guessable default-wrong invariant, or genuine breadth. Accept **Orion-only solves with Nova failing at 36–79 msgs** as a *valid Hard equilibrium* (mangum, gorm), not a calibration failure.

**7. What data is MISSING that would help future projects** (genuine gaps in the logs):
- **Measured final pass rates** for drizzle-keyset (RQB version never batched) and relation-agg (dial-back batch unrecorded) — the two "accepted" rates are predictions/incomplete.
- **gorm's 11-run denominator** behind "9%" — only a 4–5 run local batch is itemized; the Orion-124 solve batch isn't in the local log at all.
- **Orion solve data** for the drizzle trio (all Nova-only) and **per-run Nova counts** for several failing batches.
- **A real Nova amped-vs-baseline time series** (the central question the CLAUDE.md asks — no log answers it).
- **Full Dockerfile contents** for gorm and relation-agg; **measured cheating-rate** numbers (target is `<20%` but none recorded); **explicit 3-run flakiness proofs** for the final artifacts (mandated, but only asserted as "deterministic," not demonstrated).

---

### Audit provenance

| Project | Audit verdict | Key corrections applied above |
|---|---|---|
| mangum | minor_issues | Reviewer-2 word count is an estimate (~31–33, no recorded metric); Phase 8/10 msg counts belong to the rejected root_path phase; the "80 floor" is external, source sets no Nova target |
| trpc | minor_issues | Accepted-batch Nova range 93–153 (not 88); agent-LOC median true value 1231.5 (source said 1367.5); files median true 15 (source said 16.5); target is Olympus <=30%/Mars <=40%; acceptance + BATCH#4 exist only in the centralized summary (local log ends at FIX#48/BATCH#3, Nova median 128) |
| drizzle-keyset | minor_issues | Chronological per-batch rates 60/100/80/60/100; Batch#4 median not recorded (~120 computed); files dipped to 14 at FIX#4; plagiarism 0.685 (summary) vs 0.678 (local); final RQB rate is a prediction; local header still "VALIDATING" |
| drizzle-chunked | minor_issues | Nova median 131.5 final (132.5 was BATCH#2); BATCH#1 files median not recorded; only 2 standalone BATCH blocks (final 20% in header only; BATCH#2 was two sub-batches); FIX#10 is Description/Task Quality; target band 450–500 (local) vs 450–480 (centralized) |
| drizzle-relation-agg | clean | No single final pass rate; cap inconsistency (local Mars <=30% vs centralized Olympus <=20%) |
| gorm-keyset | clean | 9% cross-run vs 25%/20% local batch; Orion-124 solve not in local batch; solver LOC 1511 (summary) vs 947 (local Nova batch); Nova local median 36/39 |
