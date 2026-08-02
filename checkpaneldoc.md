checkpanel
shadow review + verdict calibration
Dashboard
Submissions
Calibrations
Tokens
Docs
https://check-cifi.onrender.com
User Two
Sign out

Documentation

Overview
Agent guide
Checks
Calibration
checkpanel
Audience: everyone. Start here, then read agent-guide.md if you are an agent and SETUP.md (repository root) if you are a human standing the thing up.

What it is
checkpanel runs local replicas of the review checks a coding-task submission will face, stores the platform's real verdict when it arrives, and measures the gap between the two.

Three things, in that order:

Replicas. Five checks, each a reconstruction of a real platform check from its stored verdicts. You run them against your artifacts before you submit, and they tell you what the real check is likely to say.
Capture. Every artifact bundle you check is stored as a content-hashed revision, and every platform verdict binds to one. That is what makes it possible, afterwards, to tell a fixed finding from a finding the platform raised against bytes you no longer have.
Calibration. Each local run can be scored against the platform verdict for the same revision, finding by finding. That is how the replicas get better against evidence instead of intuition.
It is advisory. A PASS is a prediction.
This panel is not the platform and has no authority over it. A PASS here means "the local replica did not flag anything". It is not clearance to submit, not an approval, and not a passed review. Never report it as one.

Two independent reasons the distinction matters:

The replica is a reconstruction. Its rubric is a prompt written from stored verdicts, not the platform's own code, and calibration.md is the honest measure of how far apart they are.
The real checks are not deterministic. The same artifact judged twice comes back differently. One test rated "very fair, strong repo precedent" in one round was flagged unfair in the next, citing the same repository lines as evidence. A prior PASS is not permanent clearance for the platform either.
The stale-artifact problem, in one paragraph
feature.md is not tracked in the submission repository and does not travel with test.patch. So the platform routinely judges a different copy of the description from the one you are editing. When that happens, re-running the check reproduces the same flag forever and editing against the verdict edits text the checker never saw. checkpanel detects it by checking every quoted span in a verdict against the revision the verdict claims to judge: any quote that is absent means the platform read different bytes. The fix is always to resync the artifact in the submission system first, never to re-run.

The five checks
Check	Judges	Decided by
description-quality	the spec's prose	a model
test-fairness	whether each test is solvable from the spec	a model
solution-quality	the reference implementation	a model
auto-review	the three above, synthesised	a model
false-positive	whether the suite grades what the spec states	pytest
false-positive is the odd one and deliberately so: no model decides it. The server generates deliberately wrong implementations, you run them against the real suite in your own checkout, and a mutant the suite still passes is the finding. See checks.md.

Connecting an agent to it
Two ways. Use the hosted one unless you are working on the panel itself.

Hosted — nothing to install
The deployed API serves the MCP endpoint from the same process, so there is no package to install and no local process to keep alive:

claude mcp add --transport http checkpanel https://check-cifi.onrender.com/mcp \
  --header "Authorization: Bearer cpk_..."
Mint the cpk_... token in the dashboard under Settings → Tokens. It is shown once.

Everyone uses their own token. Each tool call authenticates with the header on that call, which is what makes usage attributable per person in /v1/usage and revocation a per-person action — cutting off one laptop interrupts nobody else. A call carrying no token is refused rather than falling back to any server-side credential: with a fallback, everyone with the URL would inherit the access of whoever deployed the panel. The refusal arrives as the ordinary error envelope (ok: false, error_code: auth_failed, retryable: false), so an agent reports it instead of retrying.

Local stdio — for developing the panel itself
A locally installed checkpanel-mcp against a locally running API, configured with PANEL_API_URL and PANEL_API_TOKEN. One process, one user, so the token is read once from the environment at startup. See SETUP.md at the repository root.

Either way the MCP server is an HTTP client of the REST API and never opens the database, so authentication, usage accounting, idempotency and the error envelope stay implemented exactly once.

What is and is not built
Built and exercised by tests: the five check contracts, the finding matchers, verdict ingest (JSON and pasted prose), stale-artifact detection, the queue, calibration, the API-token surface, the MCP server, and the mutant bundle/results handshake.

Not exercised: the live OpenRouter call path, which needs a real API key.

Not built: the backtest runner. The gate that would replay a candidate prompt against historical verdicts before accepting it does not exist yet, and it has no data to run on regardless — of the 38 findings across the 9 stored description-quality verdicts, 0 anchor to their original feature.md. The backtest set has to be accumulated going forward, one snapshot per submission.

The dashboard does not start work. The frontend is read-only monitoring plus API-token management. Every action — snapshotting, running a check, storing a verdict, calibrating, requesting and reading mutants — happens through the REST API or the MCP tools that wrap it.

Where to go next
File	Audience
agent-guide.md	agents. The complete integration guide.
checks.md	both. One section per check.
calibration.md	both. What the numbers mean and when they mean nothing.
SETUP.md (repository root, not an MCP resource)	humans. Getting it running.
Working with an agent
How work actually gets done, and why none of it happens in this browser.

This UI does not run anything. It is a read-only window onto revisions, runs, and calibrations. There is no form here that starts a check.
Actions happen through the MCP server. The agent is already in the repo with feature.md, the test patch and the solution patch in hand — asking a human to paste those into a browser would be the wrong way round. It calls the MCP tools directly.
Mint a token at /settings/tokens. That is the only write surface left in this panel. The secret is shown once, so copy it when it appears.
Run one command to connect the agent, then let it drive. There is nothing to install — the MCP server is served by the panel itself over HTTP, so it works on any machine with Claude Code.
Connect an agent

Copy command
claude mcp add --transport http checkpanel \
  https://check-cifi.onrender.com/mcp \
  --header "Authorization: Bearer cpk_…"
Nothing to install. The MCP server is served by the panel itself, so this works on any machine with Claude Code. Each person should use their own token — usage is attributed per token, and revoking one leaves everyone else working.

Configuring by file instead of CLI
Replace the placeholder with a token from /settings/tokens. Tokens expire 3 days after last use and 30 days after creation.

Docs · checkpanel


checkpanel
shadow review + verdict calibration
Dashboard
Submissions
Calibrations
Tokens
Docs
https://check-cifi.onrender.com
User Two
Sign out

Documentation

Overview
Agent guide
Checks
Calibration
Agent guide
Audience: an authoring agent working on a coding-task submission. Read this once and you can work from it. Humans setting the panel up want SETUP.md at the repository root.

Everything here is reachable through the MCP tools. There is no dashboard action you are missing: the frontend is read-only monitoring plus API-token management, so the tools are the whole surface.

1. The rules, before the mechanics
These decide how you report a result, and getting them wrong is worse than not running the check at all.

This panel is advisory. It is not the platform.
A PASS is a calibrated prediction produced by a replica prompt. Never tell the user their submission "passed review", "is clear to submit", or "was approved" on the strength of anything here. Say what happened: the local replica did not flag anything.

Verdicts are not deterministic
The same artifact judged twice comes back differently, and this is observed behaviour of the real checks, not sampling noise unique to the replica: one test rated "very fair, strong repo precedent" in one round was flagged unfair in the next, citing the same repository lines as evidence.

So: re-judge every round. Do not carry a verdict forward across an edit, and do not tell the user something is settled because it passed before.

description-quality: any comment means FAIL
There is no severity, no threshold, and no "minor" comment. One comment is a FAIL and five comments are a FAIL. If a result reports "3 comments", that is a failing result with three things to fix — never "a mostly-passing run with minor notes". Every comment must be addressed or explicitly contested, and fixing beats contesting unless the comment would remove an identifier a solver needs.

Do not paste the checker's suggestion text
Every comment carries a suggestion. It is direction, not safe-harbour wording. Sentences written from the checker's own round-one suggestions have themselves been flagged in a later round. Rewrite in the author's plain prose, addressing the underlying objection.

Grep before you cut
Before deleting or compressing any clause on description-quality advice, search the test file for what that clause entails. The checks pull against each other: description-quality wants prose trimmed, and test-fairness fails a hidden test that asserts something the spec no longer states. A documented incident had a single description fix produce seven test-fairness failures.

If a clause is load-bearing for a test, the fix is to loosen the test to a behavioural postcondition first, or to restate the clause in plainer language — not to delete it.

Do not speculatively refactor
Change what was flagged. Wording the checker read and did not flag is wording that passed; rewriting it is unpaid risk. The observed pattern is that untouched accepted text stays accepted while newly-written text draws new comments.

Keep identifiers the tests pin
Option keys, export entry points, error tokens, and any other identifier the hidden tests match verbatim stay in the spec even when flagged for tone. Solvability beats style: a spec that reads beautifully and cannot be solved is a worse artifact than one with a slightly clinical sentence in it. If such an identifier is flagged, contest it, naming the specific test that depends on it.

No fleet statistics
There is no solver-agent fleet behind these tools and no pass-rate telemetry. Never invent, cite, or estimate figures like "82% of solver agents fail this". The only numbers available are the ones the tools return, and the only aggregate one is calibration_summary.

2. The workflow
snapshot ─► run checks ─► read findings ─► fix ─► re-run
                                                   │
                              (platform verdict arrives)
                                                   ▼
                                  submit_platform_verdict ─► calibrate
Snapshot at submit time, every time. feature.md is not tracked in the submission repo and does not travel with test.patch, so a verdict whose input was never captured is an orphan: afterwards there is no way to tell whether a flagged quote was fixed or whether the platform was reading an older file. run_check snapshots for you; snapshot_revision is the explicit form.

Run the checks that apply. list_checks says which are runnable and which artifacts each is entitled to; a check whose required artifact is absent is refused at enqueue rather than run against (absent).

Read the findings under the rules above, fix, and re-run — a new snapshot each time, so each round is its own revision.

When the platform's verdict lands, paste it verbatim with submit_platform_verdict, including on a PASS. That is what turns the panel from a guess into a calibrated guess. Check the response for stale_suspected and unmatched_quotes before you act on anything in it.

Then calibrate(run_id, ground_truth_id), which scores your local run against the platform's verdict finding by finding.

The false-positive probe is a separate loop; see section 6.

3. Every tool, and when to call it
Reading the surface
Tool	Call it when
list_checks	before your first run, to see what is registered and runnable
list_docs	to find these documents; they are also MCP resources
list_checks returns per check: name, requires (the artifacts it sees), ready (false means it is registered but has no prompt file, so a run would fail at enqueue), prompt_version, and executes_mutants (true only for false-positive, whose verdict comes from running tests).

Capturing artifacts
Tool	Call it when
snapshot_revision	at submit time, every time
get_revision	you need the exact bytes a verdict was bound to
list_revisions	the work was not done in this session
snapshot_revision(slug, feature_md, test_patch, solution_patch, repo, tier, repo_url, base_commit, test_command) returns revision_id — the id every later call binds to — plus content_hash and reresolved_verdicts (how many stored verdicts were re-resolved against the new head; see section 5).

The last three arguments matter only for the mutant probe. Capture base_commit (git rev-parse HEAD) if there is any chance you will run one: without it the mutant bundle has nothing to verify the tree against, and the probe cannot safely run.

list_revisions returns summaries only — has_test_patch and has_solution_patch tell you which checks that revision can support. get_revision returns the bodies, plus is_head (false means a newer revision of the same submission exists, so findings on this one may already be superseded).

Running checks
Tool	Call it when
run_check	you want a check run; it snapshots, enqueues and polls
get_run	polling a run run_check handed back as still running
list_runs	finding a run_id from a run started elsewhere
run_check(slug, check_name, feature_md, test_patch, solution_patch, samples, wait_seconds, model).

samples defaults to 1 here, against the web UI's 3: a human reading a verdict wants the vote, an agent mid-edit wants the answer, and three samples of an advisory signal is three times the cost for a difference that rarely changes what you do next.

model overrides the server default. The one time you need it is error_code: context_too_long, whose guidance is to use a larger-context model.

run_check cannot run false-positive — the API refuses it, because that check is decided by executing mutants rather than by a model. Use request_mutants.

list_runs(revision_id, status, limit) filters on pending | running | complete | failed. Only a complete run is worth calibrating: a failed one has no verdict and no findings, so scoring it records a miss that says nothing about the replica.

Ground truth and calibration
Tool	Call it when
submit_platform_verdict	the platform's verdict arrives — every round
check_verdict_freshness	you want the staleness answer and nothing stored twice
calibrate	scoring one run against one verdict
calibration_summary	the user asks how much to trust the replica
check_verdict_freshness ingests the verdict as a side effect — freshness is computed during ingest and the API has no read-only freshness route. Call it instead of submit_platform_verdict, not as well as; calling both stores the verdict twice.

calibration_summary returns {"n": 0} when nothing has been calibrated. Read n before anything else (see calibration.md).

Mutants — the false-positive probe
Tool	Call it when
request_mutants	starting a probe; the server generates and stops
list_mutant_batches	picking a batch back up
get_mutant_bundle	you are about to run the mutants yourself
submit_mutant_results	posting what pytest said
get_mutant_batch	reading progress, and the finding
Full loop in section 6.

What is deliberately not here
Creating or editing prompt versions. A grader an agent can rewrite stops being a grader. This is enforced by which tools exist, not by a role check.
Minting or revoking API tokens. That is the dashboard's job; a tool that authenticates with a token in order to mint a token is circular.
4. The async run model
POST /v1/runs returns 202. The run is enqueued and a worker executes it; a three-sample run takes minutes.

But a tool call is request/response and your client has a timeout, so run_check splits the difference: it enqueues, then polls with 1s → 5s backoff for wait_seconds (default 90).

Finished inside the window → the full result, samples and all.
Still going → {"ok": true, "status": "running", "run_id": ..., "next": "call get_run(run_id) to poll"}.
A running result is not a failure and not a timeout error. Do not re-run — that enqueues a second run of the same work and pays for it. Poll get_run(run_id).

status is pending | running | complete | failed. Only the last two are terminal.

Reading a finished run
get_run and run_check both return the run plus three added fields:

comment_count — the largest finding count across samples, restated because a bare "3" invites describing a failing run as mostly fine.
reading_rule — the rule that applies to this specific result.
advisory — the reminder that this is not the platform's decision.
Each entry in samples carries verdict, raw (the check's contract payload), reasoning, token counts and latency_ms. The run-level verdict is the vote across samples.

A failed run is not a passing check
ok arrives from the transport layer meaning "the HTTP call succeeded". A run that failed to execute would otherwise come back ok: true with a null verdict and get reported as a completed review, so the tools override it: a run with status: "failed" comes back ok: false, with outcome: "the check did NOT run" and a reading_rule saying so. Do not report it as a pass, a fail, or a completed check.

5. Stale artifacts — the loudest failure mode
feature.md is not tracked in the submission repo and ships separately from test.patch, so the platform routinely judges a different copy from the one you hold.

When a verdict lands, every quoted span in it is checked against the revision it binds to, and each finding is resolved into one of three states:

State	Meaning	What it does to you
live	the span is in the judged revision and in current head	a real open issue
superseded	in the judged revision, gone from head	you already fixed it before the verdict arrived; not held against the replica
orphan	absent even from the revision the verdict claims to judge	the platform read different bytes
submit_platform_verdict returns live, superseded, orphan, stale_suspected, and unmatched_quotes (the orphan quotes themselves).

If stale_suspected is true or unmatched_quotes is non-empty, stop. Re-running reproduces the identical flag forever — repo-side work cannot clear a flag against a description the panel never saw — and acting on the verdict edits the wrong text. The corpus documents one flag surviving three consecutive runs for exactly this reason. Resync the artifact in the submission system, snapshot it again, and only then re-run.

Snapshotting a new revision re-resolves every stored verdict for that submission against the new head, which is why snapshot_revision reports reresolved_verdicts: a finding that was live yesterday becomes superseded the moment the span it quotes is edited out.

6. The mutant / false-positive loop, end to end
A false positive is a requirement the description states and the test suite does not grade. An implementation that meets everything except that requirement passes anyway, which means the verifier is broken.

The way to find one is to build wrong implementations and see which ones the suite still passes. No model decides this. The generator proposes specimens; pytest's exit code is the verdict. That separation exists because this project's history records two reviewers confidently agreeing on a divergence that empirically did not exist, and the rule that came out of it is to apply the patch and run it rather than predict.

The server never executes anything
request_mutants enqueues; a worker calls the generator, writes the mutants, sets the batch to awaiting_execution, and stops. That is the whole of the server's involvement. It has no Docker requirement, never clones a repository, and never shells out.

Two reasons, either sufficient alone. Correctness: the suite is known to pass in the author's checkout — that interpreter, that virtualenv, those native extensions — and a server-side container is a guess at that environment whose wrong answers look exactly like right ones. Security: mutant patches are model-generated code, and running them on the API host is the worst available option.

So you run them, in the checkout.

Step by step
0. Snapshot with base_commit. The revision needs solution_patch (there is no reference implementation to make wrong without it) and test_patch (there is no suite to run against). Capture base_commit too, or step 2 has nothing to verify against.

1. request_mutants(revision_id, requested=8). Returns batch_id. requested is the number of real mutants (1..20); the generator adds exactly one control on top. Generation is a model call — poll get_mutant_batch until the status is awaiting_execution.

Pass idempotency_key if you might retry: created: false means an existing batch was returned rather than a second one paid for. That is success.

2. get_mutant_bundle(batch_id), then VERIFY THE TREE. The bundle carries base_commit, repo_url, test_command, test_patch, test_patch_hash, and the mutant patches.

Before applying anything:

git rev-parse HEAD must equal base_commit;
git status --porcelain must be empty;
the test patch must hash to test_patch_hash (sha256 of the UTF-8 bytes) and apply cleanly (git apply --check).
Refuse to run on any mismatch, and report all of them at once. Mutant diffs are written against that specific tree; against any other they either fail to apply (visible) or apply to shifted context (invisible and wrong). The suite still runs and still prints numbers. Results from the wrong tree are worse than no results.

The bundle deliberately withholds each mutant's rationale and target_sentence. Your job at this stage is to report an exit code; knowing what a mutant was supposed to break invites deciding the outcome from the story rather than observing it.

3. Per mutant: apply, run, record, RESET.

git apply <mutant patch>
<test_command>            # default: python -m pytest -q
# record the result
git checkout -- .
git clean -fd             # never -x
git clean -x would delete the virtualenv and the build caches the suite needs.

Failing to reset silently corrupts every result after the first — the second mutant runs on top of the first, the suite still executes, and every number from there on is meaningless.

If the patch does not apply, record applied_cleanly: false and move on. That is a generator bug, not a finding.

4. Never let a mutant touch a test file. If a patch modifies a test file, a conftest, or test.sh, do not run it: record it and report it to the user. A mutant that edits the tests proves nothing in either direction.

5. submit_mutant_results(batch_id, results). One dict per attempted mutant:

{
  "mutant_id": 12,
  "passed_suite": false,
  "exit_code": 1,
  "tests_passed": 68,
  "tests_failed": 2,
  "failing_tests": ["tests/test_x.py::test_nested"],
  "log_excerpt": "...",
  "applied_cleanly": true,
  "duration_ms": 41230
}
passed_suite: true means the suite still passed with the mutant applied — that is the survivor condition. Idempotent by mutant id, so a post that failed halfway can be retried with the whole set; the tally is recomputed from stored rows rather than incremented. Posting a mutant id belonging to another batch rejects the entire post.

The batch goes complete once every mutant has a result, and stays executing while any are outstanding — remaining lists which.

Then leave the tree as you found it. Reset once more and re-apply nothing. A stray wrong implementation left in someone's checkout gets debugged later as a real bug.

6. get_mutant_batch(batch_id) — the finding.

A surviving mutant is a confirmed false positive. passed_suite: true on a non-control mutant means a wrong implementation passed the suite, so the requirement it violates is stated in the description and graded by nothing. findings gives each survivor's family, the verbatim spec sentence it violates, and the rationale. The durable fix is to cover every member of that family, not to pin the one specimen that survived.
A failing control is the opposite defect. The control is a correct, semantically equivalent rewrite of the reference — different internal design, identical observable behaviour — so it must pass. control_passed: false (surfaced as over_rejects) means the suite rejects a correct implementation and would fail a competent solver. It is not a false positive.
applied_cleanly: false is not a finding. It is a generator bug. It is recorded, excluded from the survivor count, and must never be reported as a false positive: a mutant that never ran proves nothing about the suite.
On the author's own machine, panel-mutants run <batch-id> --repo . performs steps 2, 3 and 5 including the verification and the resets. panel-mutants verify <batch-id> --repo . checks the tree without running anything.

7. Error handling
Every tool returns ok. On failure it also returns:

Field	
error	what happened
error_code	stable machine-readable code
error_guidance	a sentence written for a human
retryable	whether trying again could possibly help
Errors come back as data, not exceptions, because an agent that catches an opaque exception cannot tell "wrong argument, fix it" from "provider hiccup, try again" — and retryable is exactly that answer.

retryable: false means looping cannot help. Report the guidance to the user instead.

Codes you will actually see:

Code	Retryable	Meaning
auth_failed	no	your API token was rejected -- the Authorization: Bearer cpk_... header on a hosted server, or PANEL_API_TOKEN over stdio (missing, revoked, expired). Can also mean the panel's own inference key was rejected
not_found	no	no such id
bad_request	no	the API rejected the arguments
conflict	no	conflicting state
insufficient_credit	no	the inference account is out of credit
no_provider_for_schema	no	no provider for that model honours strict JSON schema output
context_too_long	no	the artifacts exceed the model's context window — use a larger-context model
config_error	no	the server is misconfigured
rate_limited	yes	back off; lowering samples helps
model_unavailable	yes	no provider is serving that model right now
schema_violation	yes	the model ignored the contract
timeout / upstream_error / network_error	yes	transport or provider
unknown	yes	unexpected
network_error with status: 0 means the MCP server could not reach the panel API at all — it is down, or the URL is wrong. That is a setup problem to report, not something to retry indefinitely.

A run can also fail after enqueue. That arrives as a terminal run with status: "failed" carrying the same four fields; see section 4.

8. Quick reference
list_checks()
list_docs()

snapshot_revision(slug, feature_md, test_patch=, solution_patch=, repo=,
                  tier=, repo_url=, base_commit=, test_command=)
get_revision(revision_id)
list_revisions(slug=, limit=25)

run_check(slug, check_name, feature_md, test_patch=, solution_patch=,
          samples=1, wait_seconds=90, model=)
get_run(run_id)
list_runs(revision_id=, status=, limit=25)

submit_platform_verdict(revision_id, check_name, body, source="paste")
check_verdict_freshness(revision_id, check_name, verdict_body)
calibrate(run_id, ground_truth_id)
calibration_summary(check_name=)

request_mutants(revision_id, requested=8, model=, idempotency_key=)
list_mutant_batches(revision_id=, status=, limit=25)
get_mutant_batch(batch_id)
get_mutant_bundle(batch_id)
submit_mutant_results(batch_id, results)
Resources: docs://index, docs://agent-guide, docs://checks, docs://calibration.

Agent guide · checkpanel docs


checkpanel
shadow review + verdict calibration
Dashboard
Submissions
Calibrations
Tokens
Docs
https://check-cifi.onrender.com
User Two
Sign out

Documentation

Overview
Agent guide
Checks
Calibration
The checks
Audience: both. An agent needs the gates and the output shapes; a human maintaining the replicas needs the reasoning behind the input asymmetry.

Five checks are registered. list_checks (MCP) or GET /v1/checks reports which are runnable right now.

Check	Sees	Withheld	Decided by
description-quality	feature.md, test.patch	solution.patch	a model
test-fairness	feature.md, test.patch	solution.patch	a model
solution-quality	solution.patch, test.patch	feature.md	a model
auto-review	all three	—	a model
false-positive	all three	—	pytest
Why the asymmetry is deliberate
Each check sees only the artifacts it is entitled to, and the withholding is load-bearing rather than an optimisation.

A solution-quality reviewer that has read feature.md stops being independent of the description checks — it starts answering "does the implementation match the prose" instead of "is this good code", and the point of running several checks is that disagreement between them is informative.

Test-fairness is withheld solution.patch for a sharper reason: its question is "could a competent solver reading feature.md alone know to do this". What the reference implementation happens to do is not the standard, and showing it would let the check answer the wrong question convincingly.

description-quality does get test.patch, but only to answer the negative question. The real check emits a testPatchCheck for every comment, so the replica has to be able to verify whether a flagged claim is observable in the tests.

Auto-review is the exception: it is the synthesis stage, and its value comes precisely from cross-artifact reasoning — grading the reference against the description's own general clauses, and the tests against the bugs the reference actually has.

A check whose required artifact is absent is refused at enqueue, not run against (absent). Without that guard the model returns a confident verdict about nothing, which looks exactly like a right answer.

description-quality
Judges the prose of feature.md: tone, redundancy, inferable content, over-specification, and interface shape.

Does not judge the implementation, the tests' fairness, or whether the task is solvable. It has never seen solution.patch.

The gate is unconditional. Any comment at all is a FAIL. There is no severity, no threshold and no weighting in the bot form; one comment fails exactly as hard as five.

Output shape.

verdict            "PASS" | "FAIL"
summary            one sentence
evaluation.verdict same
evaluation.summary what is good, then the dominant problem
evaluation.comments[]
    category       tone | redundancy | inferable | over_specification |
                   interface_shape
    quote          verbatim span copied from the description
    suggestion     concrete rewrite instruction
    testPatchCheck { foundInTestPatch, reasoning, searchedFor }
Findings are matched by quoted span. Both sides quote verbatim from feature.md, so positional overlap is the natural join key, and one side quoting a clause while the other quotes the containing sentence still matches. Category is deliberately not part of the match — the corpus shows the platform relabelling the same span across runs (tone one round, redundancy the next), so requiring category agreement would manufacture false misses. Category disagreement is recorded separately.

Reading it: suggestion is direction, not wording to paste; grep the test file before deleting any clause it asks you to remove; leave unflagged wording alone.

test-fairness
Judges whether each test in the suite is solvable from feature.md — that is, whether a competent solver reading only the spec could know to satisfy it.

Does not judge the description's prose quality, and does not judge the reference implementation. It never sees solution.patch.

The gate is a count, not a ratio. Zero unfair entries is PASS; anything above zero is FAIL, however large the suite. "1 of 70 unfair" fails exactly as hard as "3 of 51". There is no tolerance to spend.

Every test gets a rating, but only one of the four is a finding:

Rating	Finding?
Standard external semantics	no
Prompt-stated	no
Repo-discoverable	no
Not fair	yes
The three fair ratings are the checker explaining why it did not flag something; counting them would bury the signal under a wall of approvals.

Output shape.

verdict            "PASS" | "FAIL"
unfairTestCount    zero means PASS, anything else FAIL
message            one line, e.g. "2 of 56 unfair"
overall            what is fair, then the problems
taskSummary        what the feature asks for
tests[]
    name           test function, or test_x__aspect for one split-out assertion
    verifies       what this assertion pins, as a postcondition
    evidence       a verbatim prompt quote and/or a repo path:line
    fairness       one of the four ratings
    qualityCheck   brittleness, over-coupling, redundancy
coverageSuggestions[]   advisory only, never a finding
Decomposition. The checker splits a multi-assert test into virtual per-assertion entries named test_x__aspect and rates each half separately, so one function can come back with a fair decomposition half and an unfair value-pin half. Findings are matched by test name with the __aspect suffix stripped back to the parent function — otherwise the round where the checker decomposes and the round where it does not would look like two different findings. A class-qualified name (SomeTest.test_x) is not reduced to its last segment: two suites can carry the same method name under different classes.

solution-quality
Judges the reference implementation: how comprehensively it satisfies the task, and the quality of the code.

Does not judge the description's voice. It is deliberately blind to feature.md.

The gate is graded, unlike description-quality's unconditional one:

1/3 ("Not Met") on any dimension → FAIL.
2/3 ("Partially Met") on both dimensions can still PASS, carrying the finding as a recommendation.
(The original "anything below Met fails" reading came from only ever having seen 1/3 cases; one stored submission scored 2/3 on both and passed.)

Output shape. There is no findings array. The platform emits per-dimension prose:

verdict                     "PASS" | "FAIL"
evaluation
    solution_comprehensiveness { level, score /3, max_score, reasoning }
    code_quality               { level, score /3, max_score, reasoning }
    test_results               the four runs the checker performs itself:
                               baseline_before_solution,
                               baseline_after_solution,
                               new_tests_before_solution,
                               new_tests_after_solution
    overall_feedback
Each reasoning paragraph is praise first, then the gap — and only the gap half is the finding, which is why extraction cuts at gap markers ("however", "that said", "remaining gap") and splits enumerated (1)/(2) lists rather than reading a list. A dimension at 3/3 carries no finding by construction.

Note the check reruns the tests itself, applying and un-applying solution.patch, rather than trusting the submitted fail-to-pass split. A stale registry can therefore synthesise "missing expected nodeid" failures that no visible test explains.

Findings are matched by cited code symbols, not prose. Every stored finding pins a symbol, and the corpus shows one underlying reviewer artifact re-delivered through several UIs with the prose reworded but the symbols verbatim identical. Dimension is not part of the match — the same gap is routinely filed under comprehensiveness in one delivery and code_quality in another.

auto-review
Judges everything at once. It is the synthesis gate, running after the individual checks, and the only reviewer that sees all three artifacts together.

Does not model the solver fleet. The platform's own auto reviewer also synthesises over a fleet of solver agents and cites pooled statistics ("6/12 pooled crash identically"). This replica deliberately does not: there is no fleet at check time, so any such number would be fabricated. What is replicated, and what is calibrated, is the band scores and the findings.

The gate: any band below 3/3 is a "Revision Requested". There is no weighting and no severity threshold — a submission scoring Solution 3/3 Clean was still returned for revision on Tests 1/3, and a Description 2/3 carrying only a Low finding still blocks approval.

Output shape.

verdict                "Revision Requested" | "Approved"
problem_description    { score 0-3, max_score, level, confidence }
tests                  same
solution_and_code      same
findings[]
    id                 P# (prompt), T# (tests), S# (solution), or "T3/T4"
    band               problem_description | tests | solution_and_code
    severity           High | Medium | Low
    artifact           which sub-reviewer raised it: taskQuality,
                       descriptionQuality, solutionQuality
    quote              the reviewer's reasoning line, verbatim
    expectation        the reviewer's stated remedy
takeaway               the guidance paragraph
Band levels observed: 3/3 Clean, 2/3 Minor or Partially Met, 1/3 Weak, 0/3 Failing.

Every stored auto-review verdict in the corpus is prose, not JSON — the panel delivers through a UI and verdicts are transcribed by hand. So the prose parser is a first-class part of the check, and ingest accepts either shape.

For calibration the verdict is mapped onto PASS/FAIL ("Revision Requested" → FAIL), because the outcome classifier tests whether a verdict starts with "FAIL"; returning the platform's wording verbatim would make every missed revision request look like a hit. The original wording is preserved on the contract.

Findings match when the ID agrees and the reasoning overlaps. The ID is a slot number, not an identity — S1 means "first solution finding of this run" and is reused every revision for a different bug — so matching on it alone would score a replica as perfect for guessing that a solution finding exists.

false-positive
Judges whether the test suite actually grades what the description states.

A false positive is a prompt-test completeness mismatch: the prompt states requirements A, B and C, the tests grade only A and B, and an implementation meeting A and B but not C passes anyway.

No model decides this. The generator writes deliberately wrong implementations; the suite is run against each one; pytest's exit code is the verdict. Nothing in between is a judgement call. This check is routed through the mutant engine rather than the LLM runner, and POST /v1/runs refuses it outright — list_checks marks it executes_mutants: true.

The server never executes anything. It generates mutants, parks the batch at awaiting_execution, and serves a bundle. Execution happens in the author's own checkout, where the interpreter, virtualenv and native extensions the suite is known to pass with already are. See agent-guide.md section 6 for the full loop, including the tree-verification contract.

The generator derives mutants two ways. A sentence walk — for each sentence stating a requirement, the implementation that honours every other sentence and violates that one — and a family sweep, because structural gaps hide between sentences:

Family	
naive_strategy	the obvious-but-wrong approach a hasty engineer writes from memory
promised_parameter	ignore an argument or option the spec promises is honoured
wrong_moment_state	right value, wrong moment: assignment time instead of flush time
partial_application	apply an all-or-nothing rule to only some elements
sibling_branch_guard	guard one branch, omit it from its siblings
composition_boundary	top-level case right, nested/wrapped case wrong — the highest-yield family, and at least one is always emitted
ordering_timing	violate the stated sequence while producing the same final values
deny_path_side_effect	run the side effect before refusing, so a test asserting only the refusal passes
control	not wrong: a semantically equivalent rewrite that must pass
The generator reads test.patch only for file paths, module names and signatures — never to design mutants that evade specific visible tests, which would measure its own cleverness at dodging assertions rather than whether the suite grades the spec.

Three outcomes, and only one of them is a false positive.

Result	Means
non-control mutant, passed_suite: true	confirmed false positive — the requirement it violates is stated and ungraded
control, control_passed: false	the opposite defect: the suite rejects a correct implementation and would fail a competent solver
any mutant, applied_cleanly: false	a generator bug. Recorded, excluded from the survivor count, never a finding
The survivor rule lives in exactly one function so a non-applying patch can never count on any path.

Output shape (get_mutant_batch):

batch_id, revision_id
status           pending | generating | awaiting_execution | executing |
                 complete | failed
requested, mutants_total, mutants_done, progress
survivors        int, recomputed from stored rows on every post
control_passed   bool | null
over_rejects     true when a control exists and failed
findings[]       one per survivor: family, target_sentence, rationale,
                 verdict "FALSE_POSITIVE"
mutants[]        id, idx, family, is_control, target_sentence, rationale,
                 passed_suite, applied_cleanly, failing_tests
The fix for a survivor is never to pin the specimen. A survivor names a requirement the tests do not grade; add coverage for every member of its family at once, or the next review just finds the next omission.

Platform-side ground truth for this check arrives as prose, from a panel of judges plus an adjudicator, and is matched to our survivors by cited code symbols. The training signal is asymmetric and both halves are useful: they found it and we did not means the generator lacks that family (the highest-value feedback there is); we found it and they did not means we caught it before submitting, which is the entire point and not a calibration failure.

Checks · checkpanel docs


checkpanel
shadow review + verdict calibration
Dashboard
Submissions
Calibrations
Tokens
Docs
https://check-cifi.onrender.com
User Two
Sign out

Documentation

Overview
Agent guide
Checks
Calibration
Calibration
Audience: both. An agent needs to know which number to quote and when to quote nothing; a human maintaining the replicas needs to know what the loop is measuring.

Calibration scores one local run against the platform's real verdict for the same revision. calibrate(run_id, ground_truth_id) produces it; calibration_summary(check_name) aggregates.

Why finding-level, not verdict agreement
Verdict agreement carries almost no signal here.

Every stored description-quality verdict in the historical corpus is FAIL — 9 of 9. A replica that answers FAIL unconditionally scores 100% on verdict agreement and is worth exactly nothing. Any metric a constant function can max out is not measuring the thing you care about.

So the measurement is which individual findings each side produced:

recall — of the platform's findings, how many we also raised. Low recall means we are missing triggers. This is the expensive direction: a trigger we do not have is a comment you will meet for the first time on the platform.
precision — of our findings, how many the platform also raised. Low precision means we are over-triggering, which costs you edits you did not need to make.
verdict_match is still recorded. It is just not the score.

How findings are matched
Per check, because the honest join key differs:

Check	Matched by
description-quality	overlapping quoted spans in feature.md
test-fairness	test function name, __aspect suffix stripped
solution-quality	cited code symbols
auto-review	finding ID and overlapping reasoning
false-positive	cited code symbols
Details and the reasoning behind each are in checks.md.

When a run has several samples, the one compared is the sample carrying the run's majority verdict with the most findings. Comparing the union of all samples would inflate recall; comparing a random sample would add noise.

Outcome classes
calibrate returns one of four, and they drive different work:

Outcome	Condition	What it means
MISS	platform FAIL, we PASS	highest value. A trigger the replica does not have. This is what the rubric needs to learn.
OVERCALL	platform PASS, we FAIL	we are over-triggering. Add a safe pattern.
HIT_SHALLOW	same verdict, recall below 0.5	right answer, wrong reasoning. It agreed by luck or by a different route.
HIT	same verdict, findings overlap	the replica reproduced the platform.
HIT_SHALLOW exists because "same verdict" is cheap on a corpus that is almost entirely FAIL. Separating it from HIT is what stops the aggregate looking healthy while the replica is agreeing for unrelated reasons.

live, superseded, orphan
Verdicts arrive late. By the time one lands you may already have rewritten the sentence it flags — possibly because a different check flagged the same span, or because you predicted the flag and pre-empted it.

Naively that reads as a calibration failure: the platform raised a finding our replica did not. It is not. Scoring it as a MISS would push the loop to add a rubric rule for a problem that no longer exists.

So every platform finding is resolved by checking its quoted span against two revisions — the one the verdict judged, and current head:

State	In judged revision	In head	Meaning
live	yes	yes	a real open issue
superseded	yes	no	already fixed before the verdict arrived
orphan	no	—	the platform judged bytes we never captured
recall counts all of the platform's findings.
recall_live excludes the superseded ones, and is the number to judge the replica by. Counting a finding we had already fixed punishes the replica for our own latency.
superseded_count and orphan_count are reported alongside, so a low recall next to a high superseded_count reads correctly.
The orphan case is the loud one and it is not really a calibration result at all: it means re-running the check will reproduce the flag forever, because the artifact the platform holds is not the artifact we hold. The corpus documents one flag surviving three consecutive runs for exactly that reason. Resolution is re-run whenever a new revision is snapshotted, so a finding that was live yesterday becomes superseded the moment the span it quotes is edited out.

What calibrate returns
calibration_id
outcome              HIT | HIT_SHALLOW | MISS | OVERCALL
verdict_match        bool
recall               0..1, all platform findings
recall_live          0..1, excluding superseded — prefer this
precision            0..1
superseded_count
orphan_count
prompt_version_id    which prompt produced the run being scored
missed[]             live platform findings we did not raise
overcalled[]         findings we raised that the platform did not
missed is the actionable half. Each entry carries the platform's category, quote and suggestion.

prompt_version_id is recorded on every calibration because prompts are content-addressed and versioned: a score is only meaningful attached to the exact rubric text that produced it.

calibration_summary returns n, mean_recall, mean_recall_live, mean_precision, and an outcomes histogram. With nothing calibrated it returns {"n": 0}.

The honest caveat
Aggregate numbers need roughly 15–20 paired cases before they mean anything. Below that, read calibrate output as a diagnosis of one case — "this run missed this specific trigger" — and not as a score.

There is no shortcut to getting there. The backtest gate that would replay a candidate prompt against historical verdicts, accepting a change only if recall improves and nothing regresses, is not built, and it would have no data to run on if it were: of the 38 findings across the 9 stored description-quality verdicts, 0 anchor to their original feature.md, and only 5 match any surviving feature.md at all. Every flagged quote was fixed — that is what the workflow is for — and rejected submissions were replaced wholesale. The verdicts survived; their inputs did not.

Which is the whole argument for snapshotting at submit time, every time. The paired set has to be accumulated going forward, one snapshot per submission, and a verdict whose input was never captured is an orphan that can never join it.

Do not extrapolate beyond what these numbers cover. There is no solver-agent fleet behind this system and no pass-rate telemetry. If a figure did not come out of calibrate or calibration_summary, it does not exist.

Calibration · checkpanel docs