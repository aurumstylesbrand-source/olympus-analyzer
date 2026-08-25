import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("olympus_router.py")
SPEC = importlib.util.spec_from_file_location("olympus_router", MODULE_PATH)
router = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(router)


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.project = root / "project"
        self.project.mkdir()
        self.config = root / "config" / "profiles.json"
        self.state = root / "profiles"
        self.browser_state = root / "browser"
        self.identity_key = root / "config" / "identity.key"
        self.patchers = [
            mock.patch.object(router, "PROFILES_PATH", self.config),
            mock.patch.object(router, "PROFILE_STATE_ROOT", self.state),
            mock.patch.object(router, "BROWSER_STATE_ROOT", self.browser_state),
            mock.patch.object(router, "IDENTITY_KEY_PATH", self.identity_key),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temp.cleanup()

    def add_profile(self, name="account-one"):
        router.command_profile_add(type("Args", (), {"name": name, "chrome_profile": "Chrome Profile 1"})())

    def bind_and_enable(self, allow="standard", budget="50", mode="normal", ttl="30m"):
        self.add_profile()
        router.command_bind(type("Args", (), {
            "project": str(self.project), "profile": "account-one",
            "url": "https://shipd.ai/quests/olympus/challenges/abc123", "replace": False,
        })())
        router.command_autopilot_on(type("Args", (), {
            "project": str(self.project), "mode": mode, "budget": budget,
            "ttl": ttl, "allow": allow, "observed_drip_rate": None,
        })())

    def phase_artifact(self, phase):
        path = self.project / f"{phase}.json"
        path.write_text(json.dumps({"phase": phase}) + "\n")
        return path

    def json_artifact(self, name, payload):
        path = self.project / name
        path.write_text(json.dumps(payload, indent=2) + "\n")
        return path

    def complete_phase(self, phase, *, receipt=None, result=None):
        operation = router.PHASE_OPERATION.get(phase)
        if receipt and operation:
            router.command_record(type("Args", (), {
                "project": str(self.project), "operation": operation, "cost": "0",
                "live_balance": None, "receipt": receipt,
            })())
        router.command_workflow_complete(type("Args", (), {
            "project": str(self.project), "phase": phase,
            "artifact": str(self.phase_artifact(phase)), "receipt": receipt, "result": result,
        })())

    def test_rejects_untrusted_url_shapes(self):
        bad = [
            "http://shipd.ai/quests/olympus/challenges/a",
            "https://evil.example/quests/olympus/challenges/a",
            "https://shipd.ai/quests/olympus/challenges/a?x=1",
            "https://shipd.ai/other/a",
        ]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(router.RouterError):
                router.canonical_submission_url(value)

    def test_unbound_project_reports_both_missing(self):
        payload = router.status_payload(self.project)
        self.assertEqual(payload["missing"], ["profile", "submissionUrl"])
        self.assertFalse(payload["bound"])

    def test_named_profile_aliases_are_canonical(self):
        self.assertEqual(router.profile_name("1"), "aurum")
        self.assertEqual(router.profile_name("AURUM"), "aurum")
        self.assertEqual(router.profile_name("2"), "olathedev")
        self.assertEqual(router.profile_name("OLATHEDEV"), "olathedev")

    def test_profile_uses_connected_chrome_without_exported_storage_state(self):
        self.add_profile("aurum")
        profile = router.require_registered_profile("1")
        self.assertEqual(profile["browserMode"], "connected-chrome")
        self.assertNotIn("browserStatePath", profile)
        self.assertEqual(profile["aliases"], ["1", "aurum"])

    def test_visible_identity_is_fingerprinted_and_mismatch_blocks(self):
        self.add_profile("aurum")
        router.command_profile_verify(type("Args", (), {
            "name": "1", "visible_account": "Aurum Account",
        })())
        profile = router.require_registered_profile("aurum")
        self.assertNotEqual(profile["accountFingerprint"], "Aurum Account")
        router.command_profile_check(type("Args", (), {
            "name": "AURUM", "visible_account": "  aurum   account ",
        })())
        with self.assertRaises(SystemExit) as caught:
            router.command_profile_check(type("Args", (), {
                "name": "1", "visible_account": "Olathedev Account",
            })())
        self.assertEqual(caught.exception.code, 14)

    def test_live_policy_encodes_user_budget_and_solver_rules(self):
        policy = router.live_policy_payload()
        self.assertEqual(policy["normalMode"], {
            "slashCommand": "/autopilot-on",
            "budgetTokens": "50",
            "renewal": "PAUSE_AND_ASK",
        })
        self.assertEqual(policy["overnightMode"]["slashCommand"], "/overnight")
        self.assertEqual(policy["overnightMode"]["missionBudgetTokens"], "150")
        self.assertEqual(policy["overnightMode"]["ttlHours"], 6)
        self.assertEqual(policy["overnightMode"]["absoluteMissionCeilingTokens"], "250")
        self.assertEqual(policy["deactivateCommand"], "/autopilot-off")
        self.assertEqual(policy["goldDripRateTokensPerHour"]["planningValue"], "30")
        self.assertFalse(policy["goldDripRateTokensPerHour"]["isHourlySpendQuota"])
        self.assertFalse(policy["literalUnlimitedBudgetAllowed"])
        self.assertEqual(policy["verifierCompletenessAudit"], "SKIP")
        self.assertTrue(policy["scopeGateRequiredBeforeAutoReview"])
        self.assertEqual(policy["preBatchAutoReview"]["maximumAttempts"], 3)
        self.assertEqual(policy["preBatchAutoReview"]["success"], "APPROVED")
        self.assertEqual(policy["profileChoices"], {"1": "AURUM", "2": "OLATHEDEV"})
        self.assertEqual(policy["precheckWarningAllowlist"], [
            "Problem Description Contains Only Necessary Information",
            "Dockerfile Guidelines",
        ])
        self.assertEqual(policy["testFairnessBulbs"], {"advisoryMaximum": 4, "investigateAt": 5})
        self.assertEqual(policy["agentRuns"]["solver"], "Nova")
        self.assertEqual(policy["agentRuns"]["forbiddenSolvers"], ["Orion", "Vega"])
        self.assertEqual(policy["agentRuns"]["initialCount"], 5)
        self.assertEqual(policy["agentRuns"]["standardTotal"], 10)
        self.assertEqual(policy["agentRuns"]["extraNearMissCount"], 3)
        self.assertEqual(policy["agentRuns"]["majorityNewTestFailureStopAbove"], 6)
        self.assertEqual(policy["platformInstability"]["pauseAfterConsecutiveCouldNotCompleteAbove"], 5)
        self.assertEqual(policy["terminalOrder"], ["FP", "solvability", "post-batch Auto Review"])

    def test_normal_mode_is_hard_capped_at_fifty_and_does_not_auto_renew(self):
        self.bind_and_enable()
        binding = router.load_binding(self.project)
        self.assertEqual(binding["autopilot"]["mode"], "normal")
        self.assertEqual(binding["autopilot"]["budgetTokens"], "50")
        self.assertEqual(binding["autopilot"]["releasedTokens"], "50")
        evidence = self.json_artifact("normal-release.json", {
            "missionId": binding["autopilot"]["missionId"],
            "evidencePaths": [str(self.phase_artifact("normal-proof"))],
            "newEvidence": ["local floor improved"],
            "noUnknown": True,
            "noBlockingFinding": True,
            "nextOperation": "upload",
            "nextCostTokens": "10",
        })
        with self.assertRaisesRegex(router.RouterError, "must ask the user"):
            router.command_autopilot_release(type("Args", (), {
                "project": str(self.project), "evidence": str(evidence),
            })())
        router.command_autopilot_off(type("Args", (), {"project": str(self.project)})())
        with self.assertRaisesRegex(router.RouterError, "at most 50"):
            self.bind_and_enable(budget="51")

    def test_autopilot_off_deactivates_overnight_mode(self):
        self.bind_and_enable(budget="150", mode="overnight")
        self.assertEqual(router.status_payload(self.project)["autopilot"]["effectiveState"], "on")
        router.command_autopilot_off(type("Args", (), {"project": str(self.project)})())
        self.assertEqual(router.status_payload(self.project)["autopilot"]["effectiveState"], "off")
        with self.assertRaisesRegex(router.RouterError, "off or expired"):
            router.command_can(type("Args", (), {
                "project": str(self.project), "operation": "upload", "cost": "1", "live_balance": "50",
            })())

    def test_overnight_releases_smallest_unique_evidence_backed_tranche(self):
        self.bind_and_enable(budget="150", mode="overnight")
        self.complete_phase("setup-context")
        self.complete_phase("local-floor")
        binding = router.load_binding(self.project)
        proof = self.phase_artifact("overnight-proof")
        evidence = self.json_artifact("tranche.json", {
            "missionId": binding["autopilot"]["missionId"],
            "evidencePaths": [str(proof)],
            "newEvidence": ["local floor is green on the current artifact hash"],
            "noUnknown": True,
            "noBlockingFinding": True,
            "nextOperation": "upload",
            "nextCostTokens": "60",
        })
        router.command_autopilot_release(type("Args", (), {
            "project": str(self.project), "evidence": str(evidence),
        })())
        binding = router.load_binding(self.project)
        self.assertEqual(binding["autopilot"]["releasedTokens"], "60")
        with self.assertRaisesRegex(router.RouterError, "already used"):
            router.command_autopilot_release(type("Args", (), {
                "project": str(self.project), "evidence": str(evidence),
            })())
        router.command_can(type("Args", (), {
            "project": str(self.project), "operation": "upload", "cost": "60", "live_balance": "80",
        })())

    def test_overnight_defaults_to_150_and_six_hours_but_releases_only_50(self):
        self.add_profile()
        router.command_bind(type("Args", (), {
            "project": str(self.project), "profile": "account-one",
            "url": "https://shipd.ai/quests/olympus/challenges/abc123", "replace": False,
        })())
        before = router.datetime.now(router.timezone.utc)
        router.command_autopilot_on(type("Args", (), {
            "project": str(self.project), "mode": "overnight", "budget": None,
            "ttl": None, "allow": "standard", "observed_drip_rate": "30",
        })())
        binding = router.load_binding(self.project)
        autopilot = binding["autopilot"]
        self.assertEqual(autopilot["budgetTokens"], "150")
        self.assertEqual(autopilot["releasedTokens"], "50")
        self.assertEqual(autopilot["protectedReserveTokens"], "20")
        expiry = router.datetime.fromisoformat(autopilot["expiresAt"].replace("Z", "+00:00"))
        self.assertGreaterEqual(expiry - before, router.timedelta(hours=5, minutes=59))

    def test_overnight_rejects_timer_only_release_and_reserve_invasion(self):
        self.bind_and_enable(budget="150", mode="overnight")
        self.complete_phase("setup-context")
        self.complete_phase("local-floor")
        binding = router.load_binding(self.project)
        timer_only = self.json_artifact("timer-only.json", {
            "missionId": binding["autopilot"]["missionId"],
            "evidencePaths": [],
            "newEvidence": ["time passed"],
            "noUnknown": True,
            "noBlockingFinding": True,
            "nextOperation": "upload",
            "nextCostTokens": "60",
        })
        with self.assertRaisesRegex(router.RouterError, "evidencePaths"):
            router.command_autopilot_release(type("Args", (), {
                "project": str(self.project), "evidence": str(timer_only),
            })())
        proof = self.phase_artifact("reserve-proof")
        reserve_invasion = self.json_artifact("reserve-invasion.json", {
            "missionId": binding["autopilot"]["missionId"],
            "evidencePaths": [str(proof)],
            "newEvidence": ["next action is priced but too large"],
            "noUnknown": True,
            "noBlockingFinding": True,
            "nextOperation": "upload",
            "nextCostTokens": "131",
        })
        with self.assertRaisesRegex(router.RouterError, "protected closeout reserve"):
            router.command_autopilot_release(type("Args", (), {
                "project": str(self.project), "evidence": str(reserve_invasion),
            })())

    def test_paid_operation_requires_current_live_balance(self):
        self.bind_and_enable()
        self.complete_phase("setup-context")
        self.complete_phase("local-floor")
        with self.assertRaisesRegex(router.RouterError, "live-balance"):
            router.command_can(type("Args", (), {
                "project": str(self.project), "operation": "upload", "cost": "1", "live_balance": None,
            })())
        with self.assertRaisesRegex(router.RouterError, "insufficient"):
            router.command_can(type("Args", (), {
                "project": str(self.project), "operation": "upload", "cost": "2", "live_balance": "1",
            })())

    def test_closeout_extension_requires_minor_evidence_and_never_exceeds_250(self):
        self.bind_and_enable(budget="150", mode="overnight")
        for phase in router.WORKFLOW_PHASES[:9]:
            receipt = f"receipt-{phase}" if phase in router.RECEIPT_PHASES else None
            self.complete_phase(phase, receipt=receipt)
        binding = router.load_binding(self.project)
        proof = self.phase_artifact("closeout-proof")
        evidence = self.json_artifact("closeout.json", {
            "missionId": binding["autopilot"]["missionId"],
            "classification": "minor-closeout",
            "confidence": "0.97",
            "requiresRedesign": False,
            "platformInstability": False,
            "unknowns": [],
            "approvalState": "REVISION_REQUESTED",
            "genuinePassers": 1,
            "fpOpen": 0,
            "fpBug": 0,
            "blockingFindings": [{"id": "AR-T1", "severity": "minor", "evidencePath": str(proof)}],
            "remainingActions": [{
                "operation": "auto-review", "costTokens": "20", "evidencePath": str(proof),
            }],
        })
        invalid = dict(json.loads(evidence.read_text()))
        invalid["genuinePassers"] = 0
        invalid_path = self.json_artifact("closeout-zero-passer.json", invalid)
        with self.assertRaisesRegex(router.RouterError, "FP-genuine passer"):
            router.command_autopilot_closeout_extend(type("Args", (), {
                "project": str(self.project), "new_budget": "250", "evidence": str(invalid_path),
            })())
        unknown = dict(json.loads(evidence.read_text()))
        unknown["unknowns"] = ["unreadable platform result"]
        unknown_path = self.json_artifact("closeout-unknown.json", unknown)
        with self.assertRaisesRegex(router.RouterError, "empty unknowns"):
            router.command_autopilot_closeout_extend(type("Args", (), {
                "project": str(self.project), "new_budget": "250", "evidence": str(unknown_path),
            })())
        major = dict(json.loads(evidence.read_text()))
        major["blockingFindings"] = [{
            "id": "AR-MAJOR", "severity": "major", "evidencePath": str(proof),
        }]
        major_path = self.json_artifact("closeout-major.json", major)
        with self.assertRaisesRegex(router.RouterError, "classified minor"):
            router.command_autopilot_closeout_extend(type("Args", (), {
                "project": str(self.project), "new_budget": "250", "evidence": str(major_path),
            })())
        with self.assertRaisesRegex(router.RouterError, "between 200 and 250"):
            router.command_autopilot_closeout_extend(type("Args", (), {
                "project": str(self.project), "new_budget": "251", "evidence": str(evidence),
            })())
        router.command_autopilot_closeout_extend(type("Args", (), {
            "project": str(self.project), "new_budget": "250", "evidence": str(evidence),
        })())
        self.assertEqual(router.load_binding(self.project)["autopilot"]["budgetTokens"], "250")
        with self.assertRaisesRegex(router.RouterError, "already used"):
            router.command_autopilot_closeout_extend(type("Args", (), {
                "project": str(self.project), "new_budget": "250", "evidence": str(evidence),
            })())

    def test_binding_is_canonical_and_autopilot_stays_off(self):
        self.add_profile()
        args = type("Args", (), {
            "project": str(self.project),
            "profile": "account-one",
            "url": "https://shipd.ai/quests/olympus/challenges/abc123/",
            "replace": False,
        })()
        router.command_bind(args)
        payload = router.status_payload(self.project)
        self.assertTrue(payload["bound"])
        self.assertEqual(payload["challengeId"], "abc123")
        self.assertEqual(payload["autopilot"]["effectiveState"], "off")

    def test_observe_is_allowed_while_off_but_mutation_is_denied(self):
        observe = type("Args", (), {"project": str(self.project), "operation": "observe", "cost": "0"})()
        router.command_can(observe)
        mutate = type("Args", (), {"project": str(self.project), "operation": "prechecks", "cost": "0.5"})()
        with self.assertRaisesRegex(router.RouterError, "off or expired"):
            router.command_can(mutate)

    def test_budget_and_operation_allowlist_block_overreach(self):
        self.bind_and_enable(allow="upload,prechecks", budget="2.5")
        with self.assertRaisesRegex(router.RouterError, "out of order"):
            router.command_can(type("Args", (), {"project": str(self.project), "operation": "prechecks", "cost": "0.5"})())
        self.complete_phase("setup-context")
        self.complete_phase("local-floor")
        self.complete_phase("upload-readback", receipt="version-1")
        router.command_can(type("Args", (), {
            "project": str(self.project), "operation": "prechecks", "cost": "0.5", "live_balance": "10",
        })())
        with self.assertRaisesRegex(router.RouterError, "not allowed"):
            router.command_can(type("Args", (), {"project": str(self.project), "operation": "submit", "cost": "0"})())
        with self.assertRaisesRegex(router.RouterError, "exceed budget"):
            router.command_can(type("Args", (), {
                "project": str(self.project), "operation": "prechecks", "cost": "3", "live_balance": "10",
            })())

    def test_paid_record_requires_receipt(self):
        self.bind_and_enable(allow="upload,prechecks", budget="2.5")
        self.complete_phase("setup-context")
        self.complete_phase("local-floor")
        self.complete_phase("upload-readback", receipt="version-1")
        with self.assertRaisesRegex(router.RouterError, "receipt"):
            router.command_record(type("Args", (), {
                "project": str(self.project), "operation": "prechecks", "cost": "0.5", "receipt": None,
                "live_balance": "10",
            })())

    def test_lease_alone_is_incomplete_and_starts_at_phase_zero(self):
        self.bind_and_enable()
        workflow = router.status_payload(self.project)["workflow"]
        self.assertFalse(workflow["complete"])
        self.assertEqual(workflow["nextPhase"], "setup-context")
        self.assertEqual(workflow["completedCount"], 0)

    def test_phase_order_and_artifact_are_enforced(self):
        self.bind_and_enable()
        with self.assertRaisesRegex(router.RouterError, "out of order"):
            self.complete_phase("local-floor")
        outside = Path(self.temp.name) / "outside.json"
        outside.write_text("{}\n")
        with self.assertRaisesRegex(router.RouterError, "inside the bound project"):
            router.command_workflow_complete(type("Args", (), {
                "project": str(self.project), "phase": "setup-context",
                "artifact": str(outside), "receipt": None, "result": None,
            })())

    def test_paid_phase_requires_server_receipt(self):
        self.bind_and_enable()
        self.complete_phase("setup-context")
        self.complete_phase("local-floor")
        with self.assertRaisesRegex(router.RouterError, "receipt"):
            self.complete_phase("upload-readback")

    def test_phase_rejects_receipt_not_recorded_in_mission_ledger(self):
        self.bind_and_enable()
        self.complete_phase("setup-context")
        self.complete_phase("local-floor")
        with self.assertRaisesRegex(router.RouterError, "mission ledger"):
            router.command_workflow_complete(type("Args", (), {
                "project": str(self.project), "phase": "upload-readback",
                "artifact": str(self.phase_artifact("upload-readback")),
                "receipt": "invented-version", "result": None,
            })())

    def test_pre_batch_auto_review_is_capped_at_three_attempts(self):
        self.bind_and_enable()
        for phase in (
            "setup-context", "local-floor", "upload-readback", "prechecks",
            "scope-gate", "quality-checks",
        ):
            receipt = f"receipt-{phase}" if phase in router.RECEIPT_PHASES else None
            self.complete_phase(phase, receipt=receipt)
        for attempt in range(1, 4):
            router.command_record(type("Args", (), {
                "project": str(self.project), "operation": "auto-review",
                "cost": "0", "live_balance": None, "receipt": f"auto-{attempt}",
            })())
        with self.assertRaisesRegex(router.RouterError, "capped at three"):
            router.command_can(type("Args", (), {
                "project": str(self.project), "operation": "auto-review", "cost": "0",
            })())

    def test_full_eleven_phase_path_is_only_ready_after_consensus(self):
        self.bind_and_enable()
        for phase in router.WORKFLOW_PHASES:
            receipt = f"receipt-{phase}" if phase in router.RECEIPT_PHASES else None
            result = "READY" if phase == "consensus" else None
            self.complete_phase(phase, receipt=receipt, result=result)
        workflow = router.status_payload(self.project)["workflow"]
        self.assertTrue(workflow["complete"])
        self.assertEqual(workflow["completedCount"], 11)
        self.assertIsNone(workflow["nextPhase"])

    def test_workflow_reset_moves_back_but_never_skips_forward(self):
        self.bind_and_enable()
        self.complete_phase("setup-context")
        self.complete_phase("local-floor")
        with self.assertRaisesRegex(router.RouterError, "skip forward"):
            router.command_workflow_reset(type("Args", (), {
                "project": str(self.project), "to": "scope-gate", "reason": "bad skip",
            })())
        router.command_workflow_reset(type("Args", (), {
            "project": str(self.project), "to": "local-floor", "reason": "artifact edit",
        })())
        self.assertEqual(router.status_payload(self.project)["workflow"]["nextPhase"], "local-floor")


if __name__ == "__main__":
    unittest.main()
