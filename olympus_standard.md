# OLYMPUS VIABILITY STANDARD

An Olympus challenge must be HARD ENOUGH TO CHALLENGE SOTA MODELS. Structural divergence
is NOT enough: a repo with many adapters/drivers/dialects can still only yield EASY,
transcribable features. The lesson from a real rejection (go-cloud): a repo was structurally
divergent, but the realistic features on it were too easy for SOTA and failed Task Quality.
So judge whether THIS repo can host a feature that is genuinely Olympus-grade, not whether
it merely has divergent folders.

A repo is olympusViable only if a STRONG, HARD, DETERMINISTIC, UNSOLVED feature clearly
exists in it, meeting ALL of:

1. GENUINELY HARD for a top model. Difficulty must come from a DISCOVERY GAP (an unfamiliar
   code path or a non-guessable invariant agents get WRONG BY DEFAULT) or genuine BREADTH
   (correct composition across many groups with no single trick). NEVER edge-case volume,
   NEVER a large API surface, NEVER "just implement X across N variants" (that is
   transcribable = too easy). The obvious first approach must be WRONG, or correct behaviour
   must require 5-10 files to agree on a data format / intermediate-state invariant.
2. SMALL SURFACE, hard BEHAVIOUR: 1-2 new public symbols. A feature needing 15-20+ new
   symbols is prescriptive and fails Description/Aligned/Fairness checks.
3. NOT ALREADY SOLVED: no open/merged PR and no existing API already does it (the #1
   rejection reason). Fits the project's philosophy (a maintainer would plausibly merge it).
4. DETERMINISTICALLY TESTABLE OFFLINE: strong hidden tests that 100% FAIL at the base commit
   and 100% PASS after the solution, with NO network/time/randomness/order dependence
   (the container runs --network none). A repo whose only interesting behaviour needs live
   services / DBs / network is a POOR fit unless a real offline core exists to scope to.
5. SOLVABLE: at least one strong agent can solve it from the description + repo alone.

Accepted envelope: Olympus pass rate <=20% of 10 runs; ~700+ LOC solution across 6+ files;
description 490-500 words, ASCII, behavioural, non-prescriptive (names WHAT not HOW).

olympusViable verdict:
- "yes"   = a strong, hard, deterministic, unsolved feature clearly exists here.
- "risky" = possible, BUT the obvious features look too easy / need careful scoping / the
            determinism or not-already-solved status is shaky. Treat as NOT yet proven.
- "no"    = the repo only yields transcribable/easy features, OR its interesting behaviour
            is non-deterministic (network/live-service bound), OR it is too small/abandoned.
Be skeptical: when in doubt between "yes" and "risky", choose "risky".
