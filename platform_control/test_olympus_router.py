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
        self.patchers = [
            mock.patch.object(router, "PROFILES_PATH", self.config),
            mock.patch.object(router, "PROFILE_STATE_ROOT", self.state),
            mock.patch.object(router, "BROWSER_STATE_ROOT", self.browser_state),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temp.cleanup()

    def add_profile(self, name="account-one"):
        router.command_profile_add(type("Args", (), {"name": name, "chrome_profile": "Chrome Profile 1"})())

    def bind_and_enable(self, allow="standard", budget="100"):
        self.add_profile()
        router.command_bind(type("Args", (), {
            "project": str(self.project), "profile": "account-one",
            "url": "https://shipd.ai/quests/olympus/challenges/abc123", "replace": False,
        })())
        router.command_autopilot_on(type("Args", (), {
            "project": str(self.project), "budget": budget, "ttl": "30m", "allow": allow,
        })())

    def phase_artifact(self, phase):
        path = self.project / f"{phase}.json"
        path.write_text(json.dumps({"phase": phase}) + "\n")
        return path

    def complete_phase(self, phase, *, receipt=None, result=None):
        operation = router.PHASE_OPERATION.get(phase)
        if receipt and operation:
            router.command_record(type("Args", (), {
                "project": str(self.project), "operation": operation, "cost": "0", "receipt": receipt,
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
        router.command_can(type("Args", (), {"project": str(self.project), "operation": "prechecks", "cost": "0.5"})())
        with self.assertRaisesRegex(router.RouterError, "not allowed"):
            router.command_can(type("Args", (), {"project": str(self.project), "operation": "submit", "cost": "0"})())
        with self.assertRaisesRegex(router.RouterError, "exceed budget"):
            router.command_can(type("Args", (), {"project": str(self.project), "operation": "prechecks", "cost": "3"})())

    def test_paid_record_requires_receipt(self):
        self.bind_and_enable(allow="upload,prechecks", budget="2.5")
        self.complete_phase("setup-context")
        self.complete_phase("local-floor")
        self.complete_phase("upload-readback", receipt="version-1")
        with self.assertRaisesRegex(router.RouterError, "receipt"):
            router.command_record(type("Args", (), {
                "project": str(self.project), "operation": "prechecks", "cost": "0.5", "receipt": None,
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

    def test_full_ten_phase_path_is_only_ready_after_consensus(self):
        self.bind_and_enable()
        for phase in router.WORKFLOW_PHASES:
            receipt = f"receipt-{phase}" if phase in router.RECEIPT_PHASES else None
            result = "READY" if phase == "consensus" else None
            self.complete_phase(phase, receipt=receipt, result=result)
        workflow = router.status_payload(self.project)["workflow"]
        self.assertTrue(workflow["complete"])
        self.assertEqual(workflow["completedCount"], 10)
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
