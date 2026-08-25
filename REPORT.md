# Olympus System Handoff Report for Claude

**Generated:** 2026-08-25  
**Scope:** Olympus/Mars only  
**Repository:** `/Users/mac/Downloads/olympus-analyzer`  
**Branch:** `main`  
**Verified repository commit before this report:** `f46951e727038bce3b0beeb57025a37ab5e9849c`  
**Audience:** A fresh Claude Code session that must continue without re-deriving or weakening the current system

---

## 1. Executive verdict

The shared Olympus workflow, Claude slash-command system, Codex port, local bounded-autopilot controller,
two-profile CLI authentication, memory mirrors, and FP integrity controls have been repaired and validated.

The current evidence supports these conclusions:

| Surface | Current verdict | Evidence |
|---|---|---|
| Canonical slash-command set | **PASS** | 17 Claude commands, 17 Codex prompts, 17 Codex Olympus skills |
| Claude-to-Codex synchronization | **PASS** | Sync verified 17 command pairs, 23 memory triples, workflow 49/49 |
| Router implementation | **PASS** | 24/24 unit tests; Python compilation passed |
| Retired-doctrine detection | **PASS** | 50 token forms tested in 3 contexts; zero misses |
| Semantic workflow checks | **PASS** | Round 2: 12/12 |
| Behavioral workflow checks | **PASS** | Round 3: 25/25 |
| Doctrinal coherence | **PASS** | Round 4: 59/59 |
| Arithmetic/outcome checks | **PASS** | Round 5: 11/11 |
| Reachability and registry parity | **PASS** | Round 6: 55/55 |
| FP DUMP integrity | **PASS at last check** | 446 headings, 442 unique IDs, marker FP-445, both canaries PASS |
| AURUM/1 CLI authentication | **PASS** | Routed status authenticated; 31 days remaining at verification time |
| OLATHEDEV/2 CLI authentication | **PASS** | Routed status authenticated; 31 days remaining at verification time |
| Account isolation | **PASS** | Routed user identities are distinct; separate credential roots |
| Identity routing | **PASS** | Both aliases have HMAC fingerprints bound; plaintext identity is not stored |
| Project/submission binding | **NOT YET DONE** | No project-specific submission URL has been supplied or bound |
| Live Shipd workflow execution | **NOT YET RUN** | No upload, check, rollout, mutation, or paid operation was triggered during setup |

This does **not** mean that every future submission is automatically ready. The system is ready to operate.
Each submission must still bind its exact Shipd URL and earn every live gate against its current artifacts.

---

## 2. Non-negotiable scope boundary

Everything in this report is scoped to **Olympus/Mars repo-based coding submissions**.

Do not transfer any of these rules, memories, pass-rate targets, FP instruments, or slash routes to ERIS, ULH,
or any unrelated project. If a fresh session is not clearly Olympus/Mars, stop and resolve scope first.

The platform and current repository are ground truth. Workflow doctrine is a prior. If executed evidence
contradicts a workflow default, name the contradiction, follow the evidence, and propose a workflow update.
Never use adaptability to skip verification, weaken a gate, omit a verdict, or claim a pass without an artifact.

---

## 3. What was installed

| Component | Installed version/state | Location |
|---|---|---|
| Olympus CLI | `@shipd-ai/olympus-cli@0.1.0` | `/Users/mac/.npm-global/lib/node_modules/@shipd-ai/olympus-cli` |
| Olympus executable | Symlink to the package entry point | `/Users/mac/.npm-global/bin/olympus` |
| Firecrawl CLI | `1.14.8` | `/Users/mac/.npm-global/bin/firecrawl` |
| Node.js | `v25.2.1` at last verification | Current system Node |
| npm | `11.6.2` at last verification | Current system npm |
| Local router wrapper | Executable shell wrapper | `/Users/mac/.local/bin/olympus-router` |
| Local browser boundary | Executable shell wrapper | `/Users/mac/.local/bin/olympus-browser` |

The package was genuinely installed, but an active non-interactive shell did not contain
`/Users/mac/.npm-global/bin` in `PATH`. The user's `.zshrc` already contains the export, so a normal interactive
terminal can refresh it with:

```bash
source ~/.zshrc
```

The canonical automation route should not call raw `olympus` directly. It should use the profile router:

```bash
olympus-router profile cli --name 1 -- <olympus arguments>
olympus-router profile cli --name 2 -- <olympus arguments>
```

This is required for account isolation, not merely PATH convenience.

---

## 4. Authentication and profile state

### 4.1 Registered aliases

| User-facing value | Canonical router name | Chrome label | CLI state root |
|---|---|---|---|
| `1` or `AURUM` | `aurum` | `AURUM` | `/Users/mac/.local/share/olympus-platform/profiles/aurum` |
| `2` or `OLATHEDEV` | `olathedev` | `OLATHEDEV` | `/Users/mac/.local/share/olympus-platform/profiles/olathedev` |

Both routed CLI identities were authenticated, were proven distinct, and had 31 days remaining when checked.
Both profiles have non-reversible HMAC identity fingerprints stored in the router registry.

### 4.2 Why the router is mandatory

The upstream Olympus CLI hardcodes credentials under:

```text
os.homedir()/.shipd/olympus/credentials.json
```

Therefore, two ordinary `olympus auth login` calls under one macOS home would overwrite the same credential file.

`platform_control/olympus_homedir_preload.mjs` overrides `os.homedir()` only inside the routed Node process.
The router sets `OLYMPUS_PROFILE_ROOT` to the selected profile's private root and launches the upstream CLI with:

```text
node --import olympus_homedir_preload.mjs <upstream CLI> ...
```

This preserves upstream CLI behavior while isolating its credential home per account.

### 4.3 Security facts

- Browser cookies remain in Chrome.
- CLI credentials remain in the profile-private CLI state roots.
- Passwords, cookies, local storage, session exports, recovery codes, and OTPs are never requested.
- The router stores an HMAC fingerprint of the visible account identity, not the plaintext identity.
- No token, email, user ID, or account name is included in this report.
- One early AURUM bearer token was accidentally pasted into chat. It was **not submitted to the CLI**; a fresh
  token was used. The exposed token should still be revoked through Shipd session/security controls if available.

### 4.4 Safe routed verification

Do not print the raw JSON to shared logs because it contains identity fields. Sanitize it or inspect it privately:

```bash
olympus-router profile cli --name 1 -- auth status --json
olympus-router profile cli --name 2 -- auth status --json
```

The last sanitized proof was:

```json
{
  "aurumRoutedAuth": true,
  "olathedevRoutedAuth": true,
  "distinctRoutedAccounts": true,
  "aurumDaysLeft": 31,
  "olathedevDaysLeft": 31
}
```

Authentication is persistent; the connected-Chrome control surface is session-dependent. A live browser phase
must still verify that the currently connected Chrome window matches the bound alias.

---

## 5. Implementation architecture

### 5.1 Repository files

| File | Responsibility |
|---|---|
| `platform_control/olympus_router.py` | Profile registry, identity fingerprints, project binding, policy, leases, budgets, operation authorization, receipts, ordered workflow state |
| `platform_control/olympus_browser.py` | Fail-closed connected-Chrome preparation boundary; never launches a substitute browser or exports browser state |
| `platform_control/olympus_homedir_preload.mjs` | Process-local override that isolates the upstream CLI credential home per profile |
| `platform_control/test_olympus_router.py` | 17 unit tests for routing, authorization, policy, receipts, phase order, and reset behavior |
| `experience.md` | Durable history and current implementation evidence for this repository |

### 5.2 Installed entry points

```text
/Users/mac/.local/bin/olympus-router
  -> /usr/bin/python3
  -> /Users/mac/Downloads/olympus-analyzer/platform_control/olympus_router.py

/Users/mac/.local/bin/olympus-browser
  -> isolated Python environment
  -> /Users/mac/Downloads/olympus-analyzer/platform_control/olympus_browser.py
```

### 5.3 Persistent state

| State | Path/pattern | Contents |
|---|---|---|
| Profile registry | `~/.config/olympus-platform/profiles.json` | Aliases, Chrome labels, CLI roots, HMAC fingerprints, verification time |
| HMAC key | `~/.config/olympus-platform/identity.key` | Local 32-byte key, mode 0600 |
| Per-profile CLI state | `~/.local/share/olympus-platform/profiles/<profile>/` | Isolated upstream CLI home and credentials |
| Project binding | `<project>/_artifacts/tools/OLYMPUS_PLATFORM_BINDING.json` | Profile, exact submission URL, challenge ID, lease, workflow state |
| Automation log | `<project>/_artifacts/tools/OLYMPUS_AUTOMATION_LOG.jsonl` | Append-only authorization/progress/receipt events |

All JSON state writes are atomic and restricted. Project bindings are local to the project; one project's URL or
receipts must never be reused for another project.

---

## 6. Authorization model

### 6.1 `/autopilot-off`

OFF blocks every new routed mutation and paid operation. It still permits read-only observation so the agent can
inspect status and reconcile already-accepted jobs by their existing server receipts. OFF does not claim that a
server job was cancelled.

### 6.2 `/autopilot-on`

ON is not merely a permission lease. It means executing the entire ordered workflow through final consensus.

Before enabling ON, the controller requires:

- a registered and identity-verified profile;
- an exact canonical Shipd Olympus submission URL bound to the project;
- a finite positive token budget;
- a finite TTL;
- an operation allowlist;
- read-only verification that the visible account, challenge, and current version match the binding.

Ordinary `/autopilot-on` defaults to **50 finite tokens**. When those 50 are used, the agent pauses paid work,
shows completed work, receipts, exact spend, current phase, blockers, and the next priced action, then asks before
any renewal. It cannot silently release another tranche. Literal unlimited mode is forbidden.

### 6.3 `/overnight`

`/overnight` is the single explicit independent-work mode. It executes the same complete 11-phase route under:

- 150 tokens and six hours initially;
- a 50-token initial working envelope;
- smallest-needed 10-token releases backed by new project-local evidence;
- a protected 20-token closeout reserve;
- one machine-checked minor-closeout extension to 200-250 absolute, only at >=95% confidence with at least one
  FP-genuine passer, 0 FP OPEN/BUG, no UNKNOWN/redesign/platform instability, and one or two minor blockers;
- a hard absolute ceiling of 250 tokens.

The user-reported Gold refill rate of 30 tokens/hour is rechecked from the live balance surface. It is planning
capacity, not an hourly throttle or spending authorization. `/autopilot-off` deactivates normal or overnight mode.

The standard allowlist contains:

```text
observe
upload
prechecks
scope-gate
quality-check
auto-review
rollout
```

These operations are excluded from the standard allowlist and require separate explicit authorization:

```text
submit
lock
edit-metadata
```

Before every mutation or paid action:

```bash
olympus-router can --project <project> --operation <operation> --cost <tokens>
```

After the server accepts it:

```bash
olympus-router record --project <project> --operation <operation> --cost <tokens> --receipt <server-receipt>
```

An unreadable trigger or result is `UNKNOWN`. UNKNOWN never authorizes guessing or automatic refiring.

---

## 7. The complete 11-phase autopilot route

```text
setup-context
    -> local-floor
    -> upload-readback
    -> prechecks
    -> scope-gate
    -> quality-checks
    -> pre-batch-auto-review
    -> agent-rollouts
    -> post-batch-triad
    -> post-batch-auto-review
    -> consensus
```

| Phase | Required action | Evidence/exit condition | Adaptation point |
|---|---|---|---|
| 1. `setup-context` | Resolve project root, read project `experience.md` and local `PLATFORM_CHECK_REPORT.md`, verify profile and exact URL binding | Project-local context artifact | Ask only for missing profile label and submission URL; never credentials |
| 2. `local-floor` | Run the full applicable local floor before touching the platform | Executed local artifact and hashes | Method adapts to repo; verification bar does not |
| 3. `upload-readback` | Upload the exact artifacts and read back the accepted version | Server receipt plus readback artifact | Any byte/version mismatch resets dependent evidence |
| 4. `prechecks` | Run Prechecks before Scope Gate | Receipt and complete verdict capture | Only the two exact warning exceptions below may remain; plagiarism blocks |
| 5. `scope-gate` | Run Scope Gate after Prechecks | Passing receipt/artifact | Must precede Auto Review |
| 6. `quality-checks` | Run all Quality checks | Every Quality check passes | Fairness bulbs follow the threshold policy below |
| 7. `pre-batch-auto-review` | Run Auto Review up to three total attempts | Displayed `APPROVED` is terminal | 3/3 is aspirational, not the definition of approval |
| 8. `agent-rollouts` | Nova-only cohort: start 5, normally reach 10, conditional final +3 | Receipts and all downloaded artifacts | Stop after first 5 if a majority independently fail more than 6 new tests; +3 only for credible diverse near-misses at 0/10 |
| 9. `post-batch-triad` | Download all run artifacts; run `/fix-agent-runs`; full five-source FP replay; then solvability | Immutable triad evidence bundle, 0 OPEN/BUG | FP first because only FP-genuine passers count toward solvability |
| 10. `post-batch-auto-review` | Auto Review the final passer set and current submission | Terminal `APPROVED` | It is intentionally last because Auto Review reads passing agents' code |
| 11. `consensus` | Run `/validate-triad` STEP 0-5 and emit the final verdict | `READY` or `NOT_READY` only | No phase may be skipped; stale evidence forces backward reset |

### 7.1 Exact Precheck policy

All failures block. Exactly these warning labels may remain warnings:

```text
Problem Description Contains Only Necessary Information
Dockerfile Guidelines
```

Plagiarism/similarity is serious and blocking.

### 7.2 VCA policy

The live **Verifier Completeness Audit is skipped**. It is not optional and not a fallback step; it is not run.
Historical VCA evidence may remain as historical evidence only.

### 7.3 Test Fairness bulb policy

- 0-4 bulbs: advisory; record and assess them, but do not auto-fix.
- 5 or more bulbs: investigate against the actual prompt and tests.
- Fix only a proven prompt-grounded gap.
- Any resulting edit owes fairness and FP backchecks.

### 7.4 Auto Review policy

- Displayed `APPROVED` is terminal, regardless of whether every lane is 3/3.
- 3/3 is an aspiration, never the definition of approval.
- Pre-batch Auto Review has a maximum of three attempts.
- After the third non-approved attempt, proceed to agent runs if every Quality check is green.
- Always run Auto Review again after the final passer set, with FP and solvability completed first.

### 7.5 Rollout policy

- Solver: Nova only.
- Orion and Vega are forbidden for this route.
- Initial cohort: 5.
- Standard total: 10.
- Conditional extra cohort: 3, only at 0/10 with credible diverse near-misses.
- If a majority of the first five each fails more than six new tests, stop and repair solvability before spending.
- More than five consecutive `could not complete, retry later` results pauses the route and alerts the user.

---

## 8. The 17 slash commands

The canonical source is `~/.claude/commands/<name>.md`. Codex prompts and skills are generated snapshots.
If a Codex slash prompt does not expand, read the canonical Claude command file in full and execute it manually.

Every command starts by reading `SYSTEM_MAP.md`, matching its own symptom router, resolving the project-local
`experience.md` and `PLATFORM_CHECK_REPORT.md`, and stating the assembled strategy.

| Command | Purpose | First routing decision | Required finish |
|---|---|---|---|
| `/autopilot-on` | Execute the complete bounded Shipd route | Resolve/verify profile and exact project URL; establish budget, TTL, allowlist | All 11 phases and READY/NOT_READY consensus |
| `/overnight` | Execute the same route under the self-work governor | Verify route and live balance; start 150/6h with 50 released | READY/NOT_READY, stop at 150 without qualifying closeout evidence, never exceed 250 |
| `/autopilot-off` | Revoke new mutation/spend authority | Inspect current lease and accepted receipts | OFF recorded; read-only observation preserved |
| `/new-sub` | Start a new invention-only submission | Repeat-repo versus fresh-repo fork, then GATE ZERO | Complete creation route and local validation state |
| `/continue` | Resume an interrupted task in the same chat | Read current experience state and newest instruction | Continue the exact open task without re-planning finished work |
| `/end` | Checkpoint a long chat | Reconcile disk, evidence, and open state | Current `experience.md` plus one `RESUME HERE` pointer |
| `/new-chat` | Reconstruct a project in a fresh chat | Current experience versus disk; recover if log is missing | State sheet reconstructed and `/catch-up` applied |
| `/catch-up` | Apply current doctrine to an older project | Manifest/ledger diff since project's last sync | Full `/validate`; advance sync marker only after evidence |
| `/pivot` | End a dying feature without losing lessons | Confirm feature death versus fixable harness problem | `PIVOT_HANDOFF.md`, archived artifacts, no repo switch |
| `/revamp` | Build a new harder feature after pivot | Require and read `PIVOT_HANDOFF.md`; rerun GATE ZERO | Entirely new core idea in the same repo |
| `/fix-prechecks` | Repair a failing Precheck | Route by plagiarism, prose, patch, JUnit, baseline, or Docker symptom | Re-run affected gates plus corpus obligations |
| `/fix-quality` | Repair Quality/fairness/flakiness/env/task/solution/description | Match exact quality symptom; read both instruments first | Every affected Quality gate green; FP and fairness backchecks |
| `/fix-agent-runs` | Diagnose pass rate, environment, unfairness, cheat flags | Fingerprint agent regime and failure histogram before edits | Genuine-pass corridor restored without weakening a real gate |
| `/fix-fp` | Intake and fix FP-panel/verifier findings | File every PASS/FAIL verdict before fixing; reproduce by execution | Automatic same-invocation `/validate-triad` STEP 0-5 |
| `/fix-auto-review` | Satisfy an Auto Review verdict | Route per lane and extract a satisfy-all demand list | Displayed `APPROVED`; do not chase 3/3 after approval |
| `/validate` | Full local simulation and five-row scoreboard | No reduced or quick mode | Executed per-stage evidence and GO/NO-GO |
| `/validate-triad` | Ordered FP -> solvability -> Auto Review pathway | Start/restart from immutable STEP 0 bundle when evidence is stale | STEP 0-5 complete; READY/NOT_READY at at least 95% confidence |

### 8.1 `/validate-triad` six-step contract

| Step | Work | Required artifact |
|---|---|---|
| 0 | Resolve/read both instruments; capture exact artifact hashes and context | `00_CONTEXT.md` |
| 1 | File every newly received PASS/FAIL verdict into the shared dump before sweeping | Verdict-intake artifact |
| 2 | Apply every current `FP_LIVE_VERDICTS.md` block and every `FP DUMP.MD` heading to the current description, tests, reference, and passer patches | One row per recounted entry; separate source/row counts; 0 OPEN; 0 BUG |
| 3 | Determine FP-genuine passers and solvability | Aim for at least 2 genuine; 1 acceptable; 0 broken |
| 4 | Run post-batch Auto Review against the final passer set | Displayed `APPROVED`; lane scores recorded |
| 5 | Reconcile contradictions, write both instruments, checksum bundle, emit verdict | READY or NOT_READY |

Any artifact edit invalidates dependent prior evidence. A transcript statement is not a triad artifact.

---

## 9. Core workflow artifacts and how they are consumed

The canonical manifest contains 49 workflow files. Round 6 requires an incoming live consumer for every manifest
artifact; manifest membership alone is not accepted as reachability.

### 9.1 Tier-0 spine

| Artifact | Operational role |
|---|---|
| `FIELD_CARD.md` | One-page current law, numbers, command registry, and pointers |
| `SYSTEM_MAP.md` | First read for every slash command; symptom-to-instrument routing |
| `STARTUP_PROMPT.md` | New-submission selection and reading protocol; contains the byte-identical command registry |
| `COMMAND_PREAMBLE.md` | Universal command opening and common obligations |
| `COMMAND_TABLE.md` | Cross-command table and doctrine coverage |
| `DOCTRINE_LEDGER.md` | Append-only doctrine changes and `/catch-up` verdict requirements |
| `MANIFEST.md` | Canonical file, command, and check inventory; detects loss and unregistered additions |
| `MAIN_GOAL.md` | Purpose/priority anchor |
| `README.md` | Workflow maintenance and scope boundaries |

### 9.2 Creation route

| Artifact | Operational role |
|---|---|
| `01_analyze.md` | Repository excavation and candidate discovery |
| `02_verify.md` | Candidate verification and fit checks |
| `03_creation_prep.md` | Contract lock and creation preparation |
| `04_create.md` | Implementation/test/description creation mechanics |
| `DIFFICULTY_GATE.md` | Six-part difficulty dossier replacing LOC/files/message gates |
| `prompt_difficulty.md` | Construction moves, solver proxy, divergence selection, wall measurement |
| `prompt_validation.md` | Validation planning and execution |
| `pre_submit_gate.md` | Complete pre-submission gates and scoreboard requirements |
| `platform_baseline.md` | Measured platform and agent baseline |
| `platform_spec.md` | Observed platform check surface |

### 9.3 FP system

| Artifact | Operational role |
|---|---|
| `FP_LAW.md` | FP entry point; seven named passes; five-source method |
| `FP_LIVE_VERDICTS.md` | Verbatim live verdict source; all blocks replayed every time |
| `/Users/mac/Desktop/OLYMPUS/FP DUMP.MD` | Shared append-only FP corpus; every heading replayed against the current submission |
| `FP_MACHINE_AUDIT.md` | Code/machine decomposition layer |
| `FP_SYSTEM.md` | Input-space axis pass |
| `FP_SYSTEM_V2.md` | Measured verdict-library pass |
| `FP_HANDBOOK.md` | Promise-minus-gate method, survivor triage, reachability |
| `fp_kill_protocol.md` | Clause decomposition, admission, kill matrix, executed floor |
| `community_fp_tips.md` | Platform/community FP canon |
| `verifier_audit_study.md` | Historical verifier-audit anatomy; live VCA remains skipped |
| `FP_AUDIT_PING.md` / `FP_MACHINE_AUDIT.md` | Pre-rollout and implementation audit prompts |
| `verify_fp_evidence.sh` | Strict accepted-library fidelity check |

The three accepted verdict libraries under `fp_evidence/*_NEW_SYSTEM.md` remain mandatory method passes. They
are not superseded by `FP_LAW.md`; `FP_LAW.md` is the entry point that names and orders them.

### 9.4 Agent-run diagnosis and convergence

| Artifact | Operational role |
|---|---|
| `prompt_fix_ai_runs.md` | Regime fingerprinting, failure histogram, D/R/S/N/W classification |
| `CONVERGENCE_LAW.md` | Zero-solve convergence method |
| `convergence.py` | Executable failure-shape counterfactual |
| `AGENT_RUNS_PING.md` | Agent-run audit handoff |
| `~/Desktop/olympus-agent-corpus/REGIME_LEDGER.md` | Current profile fingerprint library and playbooks |
| `~/Desktop/olympus-agent-corpus/NOVA_ATLAS.md` | Historical measured agent behavior; always re-fingerprint live |

### 9.5 Continuity, memory, and learning

| Artifact | Operational role |
|---|---|
| `LEARNING_LAW.md` | FIX -> STUDY -> RECORD -> ITERATE -> REVALIDATE |
| `MEMORY_LAW.md` | Evidence grades, memory ownership, promotion, and write triggers |
| Project `experience.md` | Current project's complete durable history and contradiction detector |
| Project `PLATFORM_CHECK_REPORT.md` | Current project's observed platform behavior and prediction ledger |
| Global `PLATFORM_CHECK_REPORT.md` | Cross-project read-only evidence; never the project write target |
| `OLYMPUS_MEMORY.md` in Codex mirrors | Olympus/Mars memory index; does not overwrite Codex-native `MEMORY.md` |
| `catch_up_prompt.md` | Ledger-derived project resynchronization |
| `prompt_recover_project.md` | Reconstructs a project when artifacts exist but the log is missing |
| `repeat_repo_prompt.md` | Repeat-repository route without inheriting new-feature Gate Zero |

### 9.6 Pivot, acceptance, and maintenance

| Artifact | Operational role |
|---|---|
| `pivot_protocol.md` | Feature-only pivot and lesson extraction |
| `olympus_accepted.md` | Accepted-submission debrief workflow |
| `olympus_experience.md` | Shared accepted-experience interface |
| `repo_scan_ledger.md` | Repository board/capacity scanning |
| `fix_auto_review.md` | Auto Review lane rubrics and APPROVED terminal law |
| `fix_reviewer_comment.md` | Reviewer-comment interpretation and third-state repair |
| `prompt_fix_plagiarism.md` | Same-repo plagiarism and semantic duplication repair |
| `AUDIT_PING.md` / `FP_AUDIT_PING.md` | Independent audit prompts |
| `retired_tokens.sh` | Live retired-doctrine scanner |

---

## 10. Current doctrine corrections that Claude must preserve

1. The lane is **solvability**, never survivability.
2. `/autopilot-on` means the full workflow, not merely enabling a lease.
3. Prechecks precede Scope Gate; Scope Gate precedes Auto Review.
4. Only the two exact Precheck warnings named above are tolerated.
5. Plagiarism is blocking.
6. Live VCA is skipped.
7. Every Quality check must pass.
8. Test Fairness bulbs 0-4 are advisory; 5+ triggers investigation; no bulb is auto-fixed.
9. Displayed Auto Review `APPROVED` is terminal. 3/3 is aspirational.
10. Pre-batch Auto Review is capped at three attempts.
11. Rollouts use Nova only; never Orion or Vega.
12. Standard cohort is 5 then 10; conditional +3 only under the defined 0/10 near-miss condition.
13. Ordinary budget is 50 tokens and then pause/report/ask; it never silently renews.
14. `/overnight` explicitly authorizes 150 tokens / 6 hours with evidence-gated releases and a conditional 250
    absolute closeout ceiling; `/autopilot-off` stops either mode.
15. FP, solvability, and post-batch Auto Review are one ordered problem.
16. Every fix triggers a current-submission replay against `FP_LIVE_VERDICTS.md`, `FP DUMP.MD`, and the three
    accepted FP method libraries.
17. Difficulty targets are counted in FP-genuine passers: design 20-30%, ship 10-40%, 41-50% only as spent
    margin with every passer genuine, above 50% broken, zero broken.
18. Aim for at least two genuine passes; one is acceptable; zero is broken.
19. Solver message counts, LOC floors, and file-count floors are not gates. Never pad.
20. Every command reads both project instruments before a fix and writes/re-reads both afterward.
21. A completeness check must have a canary proving it can fail.

---

## 11. Validation evidence and chronology

### 11.1 Router validation

The 24 tests cover:

- untrusted URL rejection;
- unbound-project missing context;
- exact alias canonicalization;
- connected-Chrome mode without exported browser state;
- HMAC identity verification and mismatch blocking;
- exact live policy encoding;
- the normal 50-token hard ceiling with no silent renewal;
- `/autopilot-off` deactivating an active overnight mission;
- the overnight 150-token / six-hour defaults with only 50 initially released;
- unique evidence-gated smallest-tranche release and reserve protection;
- current displayed-balance enforcement before paid operations;
- closeout-extension proof, one-use enforcement, and the 250-token absolute ceiling;
- canonical project binding with autopilot initially OFF;
- read-only observation while OFF;
- allowlist and budget blocking;
- required receipts for paid operations;
- lease-only incompleteness;
- ordered phases and project-local artifacts;
- required receipts on paid phases;
- rejection of receipts not recorded in the active mission ledger;
- three-attempt pre-batch Auto Review cap;
- the full 11-phase path reaching READY only after consensus;
- backward-only workflow reset.

### 11.2 Workflow validation

The proof remained fail-closed while concurrent sessions appended new FP entries:

1. The retired-token self-test completed successfully: 50 forms x 3 contexts, zero misses.
2. An earlier run correctly failed FP integrity when FP-436 arrived without baseline attestation; its raw receipt
   and matching msw3 records were verified before attestation.
3. The current run then stopped on FP-437 through FP-442 rather than silently blessing them.
4. Their schema, unique signatures, marker order, and project provenance were audited. FP-441 and FP-442 had
   copied the project-report label `SUBMISSION-SPECIFIC` into the FP outcome-class field; those values were
   corrected to `FALSE POSITIVE` and `GENUINE PASS` according to their recorded FAIL/PASS results.
5. All six new Verdict fields were attested only after the integrity checker reported no schema or historical
   mismatch. FP-443 and FP-444 then arrived during the final rerun; both were matched to the unctx intake,
   triad sweep, platform report, and experience ledger before their already-valid outcome classes were attested.
   FP integrity then passed at marker FP-445.
6. The new `/overnight` command initially failed two universal-preamble guards. Its canonical project-report
   route, `SYMPTOM INDEX`, corpus-law marker, and `SEVEN-PASS SWEEP` requirement were restored before resync.

Final round totals:

```text
Round 2 semantic:                 12 PASS / 0 FAIL
Round 3 behavioral:               25 PASS / 0 FAIL
Round 4 doctrinal coherence:       59 PASS / 0 FAIL
Round 5 arithmetic/outcome:        11 PASS / 0 FAIL
Round 6 reachability/registry:     55 PASS / 0 FAIL
```

### 11.3 Current FP state at report generation

```text
FP DUMP INTEGRITY PASS
headings=446
unique_ids=442
marker=FP-445
known_gaps=FP-099,FP-100
verdict_hashes=446
schema_entries=93
hash_canary=PASS
schema_canary=PASS
```

This corpus is actively written by other sessions. Claude must rerun the integrity checker before relying on
these counts. A newly appended entry is not a defect by itself; an unaudited entry must block baseline attestation.

### 11.4 Synchronization proof

The last Claude-to-Codex sync reported:

```text
17 command prompt/skill pairs
23 memory triples
workflow 49/49
```

Claude owns canonical commands and canonical Olympus memory. After any command, CLAUDE.md, or canonical memory
change, rerun:

```bash
bash /Users/mac/Downloads/olympus-analyzer/codex/sync_from_claude.sh
```

Never copy Claude's `MEMORY.md` over Codex's native `MEMORY.md`. The canonical Olympus index is installed as
`OLYMPUS_MEMORY.md` specifically to keep ownership separate.

---

## 12. Git and deployment state

Relevant commits, newest first at report preparation:

```text
f46951e docs: record isolated Olympus CLI authentication
9ca4fed feat: enforce connected Chrome Olympus autopilot policy
235269c Add bounded full-workflow Olympus autopilot
ddbe9c7 Make FP corpus replay explicit and automatic
ad79666 Record successful Olympus audit deployment
9768d01 Audit Olympus slash routing and refresh console doctrine
```

Before creating this report, local `HEAD` and `origin/main` were byte-identical at `f46951e...`.

The only unrelated repository modification was `.DS_Store`. It belongs to the user and must not be committed,
reverted, or overwritten by this work.

The earlier console deployment reached Render `live` and its public health endpoint returned `{"ok":true}`.
That evidence applies to the earlier console/doctrine deployment. The current router/authentication work is local
code pushed to GitHub; do not claim a new Render or Shipd deployment without fresh deployment evidence.

---

## 13. Known remaining work and warnings

### 13.1 Required before the first actual project run

No project/submission URL is currently bound by this report. At the first live step for a project:

1. Resolve the project root.
2. Ask for the alias (`AURUM/1` or `OLATHEDEV/2`) only if missing.
3. Ask for the exact Shipd Olympus submission link only if missing.
4. Never ask for credentials.
5. Bind it:

```bash
olympus-router bind --project <project> --profile <1-or-2> --url <exact-submission-url>
```

6. Verify context read-only:

```bash
olympus-router require --project <project>
olympus-router status --project <project>
```

7. Only then consider `/autopilot-on` with the explicit finite budget, TTL, and allowlist.

### 13.2 Exposed AURUM token

The accidentally pasted token was not used, but exposure alone matters. Revoke it through Shipd's security/session
controls if such a control exists. Do not paste replacement tokens into chat, logs, reports, or memory.

### 13.3 Historical project warnings

The retired-token gate reports historical projects that still carry retired MODE blocks and should run `/catch-up`
when resumed. This is not a current shared-system gate failure. Do not bulk-edit those projects from this repository;
apply `/catch-up` in each project's own context so evidence and logs remain correctly scoped.

The memory-occurrence gate also reports historical projects with no project-specific memory. At the last audit,
there was no currently owed memory event. Historical backlog must be handled in each project, not invented here.

### 13.4 No claim of perfection

The system is green against its current checks, and the checks have canaries. Unknown defect classes can still
exist outside current coverage. Claude must report executed evidence and avoid saying “perfect” or “no bugs.”

---

## 14. Exact operating commands for Claude

### Inspect the policy

```bash
olympus-router policy
```

### Verify both isolated CLI sessions without changing platform state

```bash
olympus-router profile cli --name 1 -- auth status --json
olympus-router profile cli --name 2 -- auth status --json
```

Do not paste raw identity JSON into a public artifact.

### Inspect a challenge under the correct account

```bash
olympus-router profile cli --name 1 -- problems view <challenge-id>
olympus-router profile cli --name 2 -- problems view <challenge-id>
```

### Bind a project

```bash
olympus-router bind \
  --project <absolute-project-path> \
  --profile <1-or-2> \
  --url <exact-shipd-olympus-challenge-url>
```

### Enable bounded autopilot

```bash
olympus-router autopilot on \
  --mode normal \
  --project <absolute-project-path> \
  --allow standard
```

Enabling this lease is only the authorization envelope. Continue through every workflow phase.

### Enable independent self-work mode

Invoke `/overnight`, which internally starts:

```bash
olympus-router autopilot on \
  --mode overnight \
  --project <absolute-project-path> \
  --allow standard
```

Use `/autopilot-off` to deactivate either mode.

### Inspect workflow state

```bash
olympus-router workflow status --project <absolute-project-path>
```

### Complete a phase

```bash
olympus-router workflow complete \
  --project <absolute-project-path> \
  --phase <phase-name> \
  --artifact <absolute-project-local-artifact-path> \
  --receipt <server-receipt-if-required>
```

The final `consensus` phase also requires:

```text
--result READY
```

or:

```text
--result NOT_READY
```

### Reset stale dependent evidence

```bash
olympus-router workflow reset \
  --project <absolute-project-path> \
  --to <earlier-phase> \
  --reason <why-evidence-became-stale>
```

Reset may move backward but can never skip forward.

### Disable autopilot

```bash
olympus-router autopilot off --project <absolute-project-path>
```

### Run the shared workflow audit

```bash
bash /Users/mac/Desktop/olympus-workflow/checks/run_all.sh
```

This can be slow because `gate_selftest.sh` deliberately injects every retired token in three contexts.

### Run FP integrity alone

```bash
python3 /Users/mac/Desktop/olympus-workflow/checks/fp_dump_integrity.py
```

Never run `--update-baseline` until every new entry has been audited for source, schema, classification,
provenance, and Verdict content.

---

## 15. Required startup sequence for Claude

Claude should do the following when receiving this report:

1. Confirm Olympus/Mars scope.
2. Read this report completely.
3. Read `/Users/mac/Downloads/olympus-analyzer/experience.md` completely.
4. Read the target project's local `PLATFORM_CHECK_REPORT.md` and `experience.md` completely before a fix.
5. Read `/Users/mac/Desktop/olympus-workflow/FIELD_CARD.md` and `SYSTEM_MAP.md` fresh from disk.
6. If a slash command is invoked, read `~/.claude/commands/<command>.md` in full; do not reconstruct it from this report.
7. Rerun cheap drift-prone checks: Git state, profile auth status, FP integrity, and project binding.
8. Preserve `.DS_Store` and all unrelated user changes.
9. Ask only for a missing profile alias and exact submission URL at the first live project step.
10. Do not request or reveal passwords, cookies, tokens, OTPs, recovery codes, or session exports.
11. Use `olympus-router profile cli` for every upstream CLI call.
12. Use connected Chrome only for browser work; do not substitute another browser or exported storage state.
13. Before every mutation/paid operation, run `can`; after acceptance, run `record` with the actual receipt.
14. Treat unreadable state as UNKNOWN and stop rather than refiring.
15. After every fix, update and re-read both operating instruments, then revalidate all dependent evidence.

---

## 16. Immediate next action

The system is ready for a real project, but no project is yet bound in this handoff.

The next user message should identify:

```text
profile: AURUM/1 or OLATHEDEV/2
submission: exact Shipd Olympus challenge URL
project: absolute local project path, if it is not already obvious from the working directory
```

Claude should then perform read-only binding verification and report the resolved account/challenge/version before
any live mutation. Ordinary `/autopilot-on` itself authorizes the 50-token default after confirmation;
`/overnight` explicitly authorizes its separate 150/6h governor.

---

## 17. Final handoff statement

**Locally validated system:** READY.  
**Two-profile Olympus CLI authentication:** READY and isolated.  
**Claude/Codex slash synchronization:** READY.  
**Project-specific live Shipd workflow:** NOT STARTED because no exact project/submission binding was supplied.  
**Safe next state:** bind one project to one verified alias, then execute the ordered workflow with receipts.
