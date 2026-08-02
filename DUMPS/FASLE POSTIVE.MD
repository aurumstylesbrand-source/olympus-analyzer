
False-positive review report
Genuine pass
Adjudicator · high confidence

This is a genuine true positive. The candidate ships a legitimate, language-neutral reflection-based reconciler (RewriteProtection) integrated into RecipeRunCycle before change recording/attribution — a different but strictly more general design than the reference's per-language ProtectedRegionService. All 63 requirement-mapped hidden tests pass (independently re-run here) and the 2730-test baseline is unregressed. The candidate's one notable behavioral change beyond the reference — disabling RPC batching for files with protected regions — was independently exercised by judge-c's RPC probe and works correctly (candidate passes like reference; base fails). The only candidate-vs-reference difference the panel surfaced (ordering of a protected item when interleaved unprotected siblings are reordered) is genuinely underspecified by the prompt and the reference does not match the ideal either, so it is not grounds to fail. No hidden-test hardcoding. Note for maintainers: the reflective wal…

I re-ran the full hidden suite (candidate + test.patch) with the cached Gradle 9.5.1 and GRADLE_USER_HOME=/home/model/.gradle: BUILD SUCCESSFUL, 63 tests across ProtectedRegionJava/Properties/Xml/Yaml/Run (22+11+6+12+12), 0 failures/0 errors, confirming the reward is genuine. My chief concern was the candidate-specific RecipeRunCycle change disabling batching for protected files (isInBatch = !hasProtectedRegion[0] && ...), i.e. the RPC path uncovered by the main hidden suite. Judge-c actually executed an RPC batching probe (ProtectedRegionRpcProbeTest) on candidate/reference/base worktrees: candidate BUILD SUCCESSFUL, reference BUILD SUCCESSFUL, base 2 failures — the candidate restores protected edits over batched RPC exactly like the reference. No fair, prompt-grounded probe discriminates candidate from reference; the one candidate-vs-reference divergence found by the panel (mixed protected+unprotected reordering) is unspecified and the reference also departs from the ideal, so it is not a discriminator.

Judge #1
Genuine pass
Legitimate, more-general reconciler passing a comprehensive requirement-mapped hidden suite; no fair discriminator found. True positive.

Judge #2
Genuine pass
Deserved pass. The candidate's language-agnostic RewriteProtection reconciler (CommentService + reflection) correctly implements every spec-required opt-out behavior, confirmed by the verifier's 63/63 hidden tests and 2730/2730 baseline. The only divergence found (mixed protected+unprotected reordering) is unspecified and shared by the reference, so it is not a fair discriminator.

Judge #3
Inconclusive
Pending.





2


False-positive review report
False positive
Adjudicator · high confidence · verdict changed by panel evidence

Genuine functional false positive. The candidate's identity validator (fast_import.go validateFastImportIdentity) is too permissive: it finds the last space for the timezone and the last '<' / trailing '>' for the email, so 'A <a@b>junk> 1 +0000' passes and a commit with a corrupt committer is stored. Native git fast-import and the reference both reject this. The hidden verifier only tested a bracket-less 'broken identity line', missing this case. Fix: require the timestamp to immediately follow the email's closing '>' with a single space (as git and the reference's parseIdent do), and add a hidden test covering trailing text after the email bracket.

Judge-c's probe imports a commit whose committer line is 'A <a@b>junk> 1 +0000'. The candidate's validateFastImportIdentity (fast_import.go:1221) only checks the pre-timestamp segment ends in '>' and contains a '<' (via LastIndexByte), so it accepts text after the email's closing bracket and silently builds a commit with a corrupt committer identity. I confirmed the discriminator by running the packaged probe: candidate FAILS (FastImport returns nil error, exit 1) while the reference PASSES (returns *FastImportError at line 2, exit 0). I independently confirmed native git 2.39.5 rejects the identical stream with 'fatal: Missing space after > in ident string' (exit 128). The prompt requires 'any malformed line ... fails, each a *FastImportError' and objects 'byte-identical to git', so rejecting this malformed identity is a fair, prompt-grounded requirement the candidate fails. The hidden suite's only malformed-identity test ('broken identity line', no brackets) never exercised this path.

Judge #1
Genuine pass
Complete, git-faithful fast-import implementation: passes all 108 golden-hash hidden tests and matches real git across 14 additional oracle probes. Deserved pass.

Judge #2
Not reviewed
agent failed and wrote no result: OpenCode exited 1: [91m[1mError: [0mUnexpected error

PermissionDenied: FileSystem.open (/home/model/.local/share/opencode/log/opencode.log)

Judge #3
False positive
False positive: the candidate accepts a malformed committer identity that Git and the reference reject, violating the prompt's line-numbered malformed-input requirement.




3


False-positive review report
Genuine pass
judge dissent
Adjudicator · medium confidence

The pass is a true positive. The one real behavioral gap surfaced by the panel (judge-c) is that anonymous, un-named recursive tables reached via typeof degrade to `any` instead of round-tripping, because the candidate only terminates cycles it can name as aliases (DeclarationGenerator.cpp:718-723), whereas the reference synthesizes fresh names for un-named cyclic types. This is a legitimate robustness improvement worth making, but it is not required by the prompt (whose recursion contract is alias-scoped) and is deliberately not covered by the hidden suite, so it does not undermine the reward. If graders want to require it, they should add a hidden test and tighten the prompt language beyond 'aliases that refer to themselves'.

Judges a and b (TP) matched my independent view. Judge-c raised a solo FP whose probe genuinely discriminates: for an anonymous typeof-derived self-referential table (local recursive={}; recursive.self=recursive; export type Surface={nested: typeof(recursive)}) the candidate emits `{ nested: { self: any } }`, losing the cycle, while the reference synthesizes names to preserve it. I confirmed the discrimination from the candidate code (DeclarationGenerator.cpp:718-723 returns "any" on re-entry of an active un-named type) and from judge-c's recorded doctest output (candidate exit 1, reference exit 0). However the probe is NOT fair: the prompt's sole recursion clause is framed entirely around aliases and the alias-name mechanism, which cannot express an anonymous cycle without synthesizing names the prompt never mentions; anonymous self-referential tables are not writable in surface annotation syntax; and the otherwise-exhaustive 94-test hidden suite (authored alongside a reference that DOES handle anon-recursion) tests recursion only via aliases and deliberately omits this case, a strong signal it was not a graded requirement. The candidate satisfies the prompt's stated (alias-based) recursion contract, so judge-c is over-flagging a stricter-than-stated contract.

Judge #1
Genuine pass
Comprehensive, legitimate declaration generator; passes all 94 hidden tests and 10 additional fair round-trip/recursion/determinism/private-alias/CLI probes. No fair discriminator found.

Judge #2
Genuine pass
Deserved pass. A thorough declaration generator implements all prompt requirements; the 94-test hidden suite passes and six adversarial falsification attempts found no fair discriminator.

Judge #3
False positive
False positive: anonymous recursive surface types are widened to any, breaking the explicitly required exact declaration round trip.




4. 

False-positive review report
False positive
Adjudicator · medium confidence · verdict changed by panel evidence

The pass is a functional false positive. The generic span-reconciler in RecipeRunOptOut.restoreProtectedSpans handles insert/delete/reorder-within-span and edits correctly, but when a recipe relocates an existing UNPROTECTED sibling into a protected span it clears the span's index range and reinserts only the original protected items, silently discarding the relocated statement. This is real data loss of unmarked code, reachable by ordinary reorder/sort recipes, and violates the prompt's 'changes anywhere else are kept / only surviving changes remain' guarantee. The reference distinguishes moved-existing items (kept, by id membership in the before-set) from genuinely-new insertions (dropped) and preserves the statement. The hidden suite never exercises a cross-boundary move, which is why the verifier missed it; add such a case. Note the separate identity-replacement gap (whole-subtree replacement with new ids) defeats BOTH candidate and reference and is a genuine specification/coverag…

I re-ran judge-b's probe in both worktrees. When a recipe MOVES an existing unprotected statement (int x = 0;) into a protected span, the candidate's restoreProtectedSpans clears the whole span range and reinserts only the original protected items, so x is silently DELETED (confirmed: candidate output drops the statement entirely). The reference PASSES the same probe (BUILD SUCCESSFUL), preserving x. This discriminates. No reading of the prompt permits an existing unmarked statement to vanish: under a strict 'the region reads exactly as before' reading x must still survive elsewhere (e.g. restored to origin), and under the reference reading x is kept adjacent to the protected items -- both require x to exist somewhere, yet the candidate produces it nowhere. This violates the prompt's guarantee that 'Changes anywhere else in the file are kept' and that a file carries 'only the surviving changes'; silent data loss of unmarked code defeats the very safety purpose of the feature and is reachable by realistic reorder/sort recipes (the suite itself uses sort/reorder recipes). judge-c's competing FP does NOT hold: its identity-replacement probe fails on the reference too (reference makes no change and loses the outside edit), so it is a shared spec-coverage gap, not a fair discriminator.

Judge #1
Genuine pass
Generic reflection-based opt-out reconciler; passes all 83 hidden tests and every fair probe (annotated-method protection, deleted-anchor restoration, inner-block scope isolation). Deserved pass.

Judge #2
False positive
False positive: the agent's generic reconciler drops moved existing items that fall in the protected span's removal range (data loss), violating 'Changes anywhere else in the file are kept.' A fair probe test discriminates — agent fails, reference passes.

Judge #3
Not reviewed
agent failed and wrote no result: Agent timed out: killed at the 1500s solver wall-clock



5. 

False-positive review report
False positive
Adjudicator · high confidence · verdict changed by panel evidence

The implementation is broad and correct across nearly every prompt requirement, but it deliberately removes page Contents from recursive field comparison (src/diff.rs:478) and replaces it with a decoded-byte-only check (src/diff.rs:346-350). Consequently any difference confined to a page content-stream's dictionary (e.g. adding a non-encoding key such as Custom) is silently dropped, producing an empty diff for two genuinely different documents. This violates the prompt's explicit rule that a one-sided dictionary key must be reported as Added/Removed. The fix is to compare the content stream's dictionary as well (as the code already does for every other stream via compare_objects_inner, skipping only Length/Filter/DecodeParms), or to keep Contents in the effective page fields and let the generic stream comparator handle both bytes and dict.

I re-ran judge-c's discriminator in isolated worktrees. Candidate (verifier worktree) returns an empty diff (`all changes = []`) when a non-encoding key `Custom=7` is added to a page's content-stream dictionary while decoded bytes are unchanged; the reference reports `page 1/Contents/Custom` Added and passes the same assertion. The prompt explicitly requires 'a key on one side only is Added or Removed' for dictionaries, and a page content stream is a Stream with an associated Dictionary in the repo's object model. The candidate special-cases page Contents (diff.rs:478 excludes it from effective page fields; diff.rs:346-350 does a decoded-byte-only check), dropping the content-stream dictionary from comparison entirely — even though its own generic stream comparator (diff.rs:650-665) compares stream dicts everywhere else. The failure is material (an empty diff for two genuinely different documents), fair, and prompt-grounded.

Judge #1
Not reviewed
agent failed and wrote no result: Agent exited with code 1

Judge #2
Genuine pass
Pass is deserved. All 50 hidden tests pass and every prompt-stated requirement holds at its hardest case. The only candidate/reference divergence (outline title-only change labeled OutlineChanged by candidate vs Removed+Added by reference) is an underspecified edge the prompt does not require, so it is not a false positive.

Judge #3
False positive
False positive: the candidate skips page content stream dictionaries when decoded bytes are unchanged, violating the explicit dictionary-entry diff requirement.



6. 

False-positive review report
False positive
Adjudicator · high confidence · verdict changed by panel evidence

The candidate is a substantive, mostly-correct implementation that passes all 113 hidden tests, but it is a genuine functional false positive on one central requirement. It restores protected regions only within lists that still exist in the post-recipe tree and lacks a global 'every protected id must still be present, else revert' guarantee (which the reference has via ProtectedRegions.containsEvery). Consequently, when a recipe deletes an unprotected ancestor (e.g. the method enclosing a fenced statement), the nested marked code is silently deleted — violating 'a protected region must read exactly as it did before' and 'a deleted one is still present'. The hidden verifier should add a case for deleting an unprotected intermediate ancestor that contains a nested protected region (analogous to the existing whole-file deletion test) to close this gap.

Judge-c's probe deletes an unprotected ancestor method that CONTAINS a nested '// rewrite:off' protected statement. I re-ran it: the candidate FAILS — its output is `class A {\n\n    void neighbor() {\n    }\n}`, i.e. the protected `int protectedValue = 1;` is entirely deleted — while the reference PASSES (protected content preserved). This directly violates explicit prompt requirements: 'a protected region must read exactly as it did before', 'a deleted one is still present', and the feature's core promise that 'recipes leave marked code alone'. The prompt even makes the ancestor case explicit at the file level ('a recipe that would delete a file holding a protected region does not'); an intermediate ancestor deletion that wipes marked code is the same obligation. Root cause: the candidate only reconciles lists still present in the post-recipe tree, so a deleted ancestor's nested protected region is never restored, and it has no global protected-id survival check. The hidden verifier covered deleting a protected SIBLING and deleting the whole FILE, but not deleting an unprotected intermediate ancestor — the incompleteness the FP exploits.

Judge #1
Genuine pass
Deserved pass: candidate implements opt-out fences across all four languages plus scheduler reporting; all 113 comprehensive hidden tests pass (re-verified), fair probes for switch-case and imports pass, and the only failing edge is shared with the reference.

Judge #2
Genuine pass
Deserved pass: a comprehensive scheduler-level protected-region implementation passes all 113 hidden tests; aggressive falsification (boundary insertions, closer-comment handling, nested-block fences, cycle/message semantics) found no fair discriminator, and the candidate matches the reference on the two ambiguous design points. The 2 visible test_execution.log failures are agent-authored tests, not verifier failures.

Judge #3
False positive
False positive: deleting a method that contains a nested protected statement deletes the protected region, even though the prompt requires it to remain exactly as before.



7. 
