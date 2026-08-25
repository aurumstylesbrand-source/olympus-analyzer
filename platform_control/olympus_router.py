#!/usr/bin/env python3
"""Safe project/account binding and authorization router for Olympus platform work.

This controller stores routing metadata only. Browser cookies remain in Chrome,
and CLI tokens remain in a profile-private CLI state directory.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from pathlib import Path
from urllib.parse import urlparse


SCHEMA_VERSION = 4
PROFILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
PROFILE_ALIASES = {
    "1": "aurum",
    "aurum": "aurum",
    "2": "olathedev",
    "olathedev": "olathedev",
}
PROFILE_LABELS = {
    "aurum": "AURUM",
    "olathedev": "OLATHEDEV",
}
CHALLENGE_PATH_RE = re.compile(r"^/quests/olympus/challenges/([A-Za-z0-9_-]+)$")
ALL_OPERATIONS = {
    "observe",
    "upload",
    "prechecks",
    "scope-gate",
    "quality-check",
    "auto-review",
    "rollout",
    "submit",
    "lock",
    "edit-metadata",
}
STANDARD_OPERATIONS = {
    "observe",
    "upload",
    "prechecks",
    "scope-gate",
    "quality-check",
    "auto-review",
    "rollout",
}
WORKFLOW_PHASES = (
    "setup-context",
    "local-floor",
    "upload-readback",
    "prechecks",
    "scope-gate",
    "quality-checks",
    "pre-batch-auto-review",
    "agent-rollouts",
    "post-batch-triad",
    "post-batch-auto-review",
    "consensus",
)
OPERATION_PHASES = {
    "upload": {"upload-readback"},
    "prechecks": {"prechecks"},
    "scope-gate": {"scope-gate"},
    "quality-check": {"quality-checks"},
    "rollout": {"agent-rollouts"},
    "auto-review": {"pre-batch-auto-review", "post-batch-auto-review"},
}
PHASE_OPERATION = {
    phase: operation
    for operation, phases in OPERATION_PHASES.items()
    for phase in phases
}
RECEIPT_PHASES = {
    "upload-readback",
    "prechecks",
    "scope-gate",
    "quality-checks",
    "pre-batch-auto-review",
    "agent-rollouts",
    "post-batch-auto-review",
}

USER_ROOT = Path("/Users/mac")
CONFIG_ROOT = USER_ROOT / ".config" / "olympus-platform"
STATE_ROOT = USER_ROOT / ".local" / "state" / "olympus-platform"
PROFILE_STATE_ROOT = USER_ROOT / ".local" / "share" / "olympus-platform" / "profiles"
BROWSER_STATE_ROOT = USER_ROOT / ".local" / "share" / "olympus-platform" / "browser"
PROFILES_PATH = CONFIG_ROOT / "profiles.json"
IDENTITY_KEY_PATH = CONFIG_ROOT / "identity.key"
CLI_ENTRY = USER_ROOT / ".npm-global" / "lib" / "node_modules" / "@shipd-ai" / "olympus-cli" / "dist" / "index.js"
PRELOAD = Path(__file__).with_name("olympus_homedir_preload.mjs")

DEFAULT_MISSION_BUDGET = Decimal("50")
OVERNIGHT_MISSION_BUDGET = Decimal("150")
DEFAULT_NORMAL_TTL = "2h"
DEFAULT_OVERNIGHT_TTL = "6h"
MAX_MISSION_TTL = timedelta(hours=6)
INITIAL_WORKING_ENVELOPE = Decimal("50")
RENEWAL_TRANCHE = Decimal("10")
PROTECTED_CLOSEOUT_RESERVE = Decimal("20")
MAX_MISSION_BUDGET = Decimal("250")
MAX_CLOSEOUT_EXTENSION = Decimal("100")
MIN_CLOSEOUT_CONFIDENCE = Decimal("0.95")
USER_REPORTED_GOLD_DRIP_RATE = Decimal("30")


class RouterError(RuntimeError):
    def __init__(self, message: str, exit_code: int = 2):
        super().__init__(message)
        self.exit_code = exit_code


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def secure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def atomic_json_write(path: Path, value: object) -> None:
    secure_dir(path.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        if tmp.exists():
            tmp.unlink()


def read_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RouterError(f"invalid JSON state at {path}: {exc}") from exc


def profile_name(value: str) -> str:
    normalized = value.strip().lower()
    normalized = PROFILE_ALIASES.get(normalized, normalized)
    if not PROFILE_RE.fullmatch(normalized):
        raise RouterError("profile must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    return normalized


def identity_key() -> bytes:
    secure_dir(IDENTITY_KEY_PATH.parent)
    if not IDENTITY_KEY_PATH.exists():
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            fd = os.open(IDENTITY_KEY_PATH, flags, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "wb") as handle:
                handle.write(secrets.token_bytes(32))
                handle.flush()
                os.fsync(handle.fileno())
    os.chmod(IDENTITY_KEY_PATH, 0o600)
    value = IDENTITY_KEY_PATH.read_bytes()
    if len(value) != 32:
        raise RouterError(f"identity key has wrong size: {IDENTITY_KEY_PATH}")
    return value


def identity_fingerprint(value: str) -> str:
    normalized = " ".join(value.strip().casefold().split())
    if not normalized:
        raise RouterError("visible account identity must not be empty")
    return hmac.new(identity_key(), normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def canonical_submission_url(value: str) -> tuple[str, str]:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or parsed.netloc.lower() != "shipd.ai":
        raise RouterError("submission URL must use https://shipd.ai")
    if parsed.params or parsed.query or parsed.fragment:
        raise RouterError("submission URL must not contain params, query, or fragment")
    hit = CHALLENGE_PATH_RE.fullmatch(parsed.path.rstrip("/"))
    if not hit:
        raise RouterError("submission URL must be /quests/olympus/challenges/<challenge-id>")
    challenge_id = hit.group(1)
    return f"https://shipd.ai/quests/olympus/challenges/{challenge_id}", challenge_id


def profile_registry() -> dict:
    data = read_json(PROFILES_PATH, {"schemaVersion": SCHEMA_VERSION, "profiles": {}})
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        raise RouterError(f"profile registry has wrong shape: {PROFILES_PATH}")
    return data


def resolve_project(value: str | None) -> Path:
    if value:
        path = Path(value).expanduser().resolve()
        if not path.is_dir():
            raise RouterError(f"project directory does not exist: {path}")
        return path
    path = Path.cwd().resolve()
    for candidate in (path, *path.parents):
        if (candidate / "_artifacts").is_dir() or (candidate / "experience.md").is_file() or (candidate / ".git").is_dir():
            return candidate
    raise RouterError("could not resolve a project root; pass --project")


def tools_dir(project: Path) -> Path:
    return project / "_artifacts" / "tools"


def binding_path(project: Path) -> Path:
    return tools_dir(project) / "OLYMPUS_PLATFORM_BINDING.json"


def automation_log_path(project: Path) -> Path:
    return tools_dir(project) / "OLYMPUS_AUTOMATION_LOG.jsonl"


def empty_autopilot() -> dict:
    return {
        "enabled": False,
        "mode": "normal",
        "expiresAt": None,
        "budgetTokens": "0",
        "baseBudgetTokens": "0",
        "spentTokens": "0",
        "releasedTokens": "0",
        "initialWorkingEnvelopeTokens": str(INITIAL_WORKING_ENVELOPE),
        "renewalTrancheTokens": str(RENEWAL_TRANCHE),
        "protectedReserveTokens": "0",
        "planningDripRateTokensPerHour": str(USER_REPORTED_GOLD_DRIP_RATE),
        "observedDripRateTokensPerHour": None,
        "closeoutExtensionUsed": False,
        "closeoutEvidenceArtifact": None,
        "allowedOperations": ["observe"],
        "missionId": None,
    }


def empty_binding() -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "profile": None,
        "submissionUrl": None,
        "challengeId": None,
        "lastVerified": None,
        "autopilot": empty_autopilot(),
        "workflow": {
            "nextPhaseIndex": 0,
            "state": "not-started",
            "result": None,
            "history": [],
        },
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }


def load_binding(project: Path) -> dict:
    data = read_json(binding_path(project), empty_binding())
    if not isinstance(data, dict):
        raise RouterError(f"binding has wrong shape: {binding_path(project)}")
    return data


def save_binding(project: Path, data: dict) -> None:
    data["schemaVersion"] = SCHEMA_VERSION
    data["updatedAt"] = now_iso()
    atomic_json_write(binding_path(project), data)


def append_event(project: Path, event: dict) -> None:
    path = automation_log_path(project)
    secure_dir(path.parent)
    record = {"at": now_iso(), **event}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    os.chmod(path, 0o600)


def receipt_is_recorded(project: Path, mission_id: str | None, operation: str, receipt: str) -> bool:
    path = automation_log_path(project)
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            event.get("event") == "operation-recorded"
            and event.get("missionId") == mission_id
            and event.get("operation") == operation
            and event.get("receipt") == receipt
        ):
            return True
    return False


def operation_count(project: Path, mission_id: str | None, operation: str, phase: str) -> int:
    path = automation_log_path(project)
    if not path.is_file():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            event.get("event") == "operation-recorded"
            and event.get("missionId") == mission_id
            and event.get("operation") == operation
            and event.get("phase") == phase
        ):
            count += 1
    return count


def require_registered_profile(name: str) -> dict:
    name = profile_name(name)
    profiles = profile_registry()["profiles"]
    if name not in profiles:
        raise RouterError(f"profile is not registered: {name}", 10)
    return profiles[name]


def parse_decimal(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise RouterError(f"invalid decimal value: {value}") from exc
    if parsed < 0:
        raise RouterError("decimal value must not be negative")
    return parsed


def parse_ttl(value: str) -> timedelta:
    hit = re.fullmatch(r"([1-9][0-9]*)([mh])", value)
    if not hit:
        raise RouterError("TTL must look like 30m or 2h")
    amount = int(hit.group(1))
    return timedelta(minutes=amount) if hit.group(2) == "m" else timedelta(hours=amount)


def parse_operations(value: str) -> list[str]:
    if value == "standard":
        return sorted(STANDARD_OPERATIONS)
    operations = {item.strip() for item in value.split(",") if item.strip()}
    unknown = operations - ALL_OPERATIONS
    if unknown:
        raise RouterError(f"unknown operations: {', '.join(sorted(unknown))}")
    operations.add("observe")
    return sorted(operations)


def autopilot_expired(binding: dict) -> bool:
    expires = binding.get("autopilot", {}).get("expiresAt")
    if not expires:
        return False
    parsed = datetime.fromisoformat(expires.replace("Z", "+00:00"))
    return parsed <= datetime.now(timezone.utc)


def workflow_payload(binding: dict) -> dict:
    workflow = dict(binding.get("workflow") or empty_binding()["workflow"])
    index = int(workflow.get("nextPhaseIndex", 0))
    workflow["complete"] = workflow.get("state") == "complete" and workflow.get("result") == "READY"
    workflow["nextPhase"] = WORKFLOW_PHASES[index] if 0 <= index < len(WORKFLOW_PHASES) else None
    workflow["phaseCount"] = len(WORKFLOW_PHASES)
    workflow["completedCount"] = min(max(index, 0), len(WORKFLOW_PHASES))
    return workflow


def autopilot_payload(binding: dict) -> dict:
    """Return a backward-compatible mission view without mutating stored state."""
    payload = empty_autopilot()
    payload.update(binding.get("autopilot") or {})
    budget = parse_decimal(str(payload.get("budgetTokens", "0")))
    if "baseBudgetTokens" not in (binding.get("autopilot") or {}):
        payload["baseBudgetTokens"] = str(budget)
    if "releasedTokens" not in (binding.get("autopilot") or {}):
        payload["releasedTokens"] = str(min(INITIAL_WORKING_ENVELOPE, budget))
    if "protectedReserveTokens" not in (binding.get("autopilot") or {}):
        payload["protectedReserveTokens"] = str(
            min(PROTECTED_CLOSEOUT_RESERVE, max(Decimal("0"), budget - INITIAL_WORKING_ENVELOPE))
        )
    return payload


def effective_spend_limit(binding: dict) -> Decimal:
    autopilot = autopilot_payload(binding)
    budget = parse_decimal(str(autopilot["budgetTokens"]))
    released = parse_decimal(str(autopilot["releasedTokens"]))
    reserve = parse_decimal(str(autopilot["protectedReserveTokens"]))
    phase_index = int((binding.get("workflow") or {}).get("nextPhaseIndex", 0))
    closeout_index = WORKFLOW_PHASES.index("post-batch-triad")
    if phase_index >= closeout_index:
        return budget
    return min(released, max(Decimal("0"), budget - reserve))


def artifact_within_project(project: Path, value: str) -> Path:
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(project)
    except ValueError as exc:
        raise RouterError("phase artifact must be inside the bound project") from exc
    if not path.is_file() or path.stat().st_size == 0:
        raise RouterError(f"phase artifact must be a nonempty file: {path}")
    return path


def project_json_artifact(project: Path, value: str) -> tuple[Path, dict, str]:
    path = artifact_within_project(project, value)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RouterError(f"evidence artifact must contain valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise RouterError("evidence artifact must contain a JSON object")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, payload, digest


def evidence_digest_used(project: Path, mission_id: str | None, event_name: str, digest: str) -> bool:
    path = automation_log_path(project)
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            event.get("event") == event_name
            and event.get("missionId") == mission_id
            and event.get("evidenceSha256") == digest
        ):
            return True
    return False


def mission_completed_phase(binding: dict, phase: str) -> bool:
    mission_id = autopilot_payload(binding).get("missionId")
    return any(
        item.get("phase") == phase and item.get("missionId") == mission_id
        for item in (binding.get("workflow") or {}).get("history", [])
        if isinstance(item, dict)
    )


def status_payload(project: Path) -> dict:
    binding = load_binding(project)
    missing = []
    if not binding.get("profile"):
        missing.append("profile")
    if not binding.get("submissionUrl"):
        missing.append("submissionUrl")
    autopilot = autopilot_payload(binding)
    if autopilot.get("enabled") and autopilot_expired(binding):
        autopilot["effectiveState"] = "expired"
    else:
        autopilot["effectiveState"] = "on" if autopilot.get("enabled") else "off"
    return {
        "project": str(project),
        "bindingPath": str(binding_path(project)),
        "bound": not missing,
        "missing": missing,
        "profile": binding.get("profile"),
        "submissionUrl": binding.get("submissionUrl"),
        "challengeId": binding.get("challengeId"),
        "lastVerified": binding.get("lastVerified"),
        "autopilot": autopilot,
        "workflow": workflow_payload(binding),
    }


def command_profile_add(args: argparse.Namespace) -> None:
    name = profile_name(args.name)
    registry = profile_registry()
    profiles = registry["profiles"]
    root = PROFILE_STATE_ROOT / name
    secure_dir(root)
    previous = profiles.get(name, {})
    profiles[name] = {
        "chromeProfile": args.chrome_profile or PROFILE_LABELS.get(name, name.upper()),
        "aliases": sorted(alias for alias, target in PROFILE_ALIASES.items() if target == name),
        "browserMode": "connected-chrome",
        "cliStateRoot": str(root),
        "accountFingerprint": previous.get("accountFingerprint"),
        "identityVerifiedAt": previous.get("identityVerifiedAt"),
        "createdAt": previous.get("createdAt", now_iso()),
        "updatedAt": now_iso(),
    }
    atomic_json_write(PROFILES_PATH, registry)
    print(json.dumps({"registered": name, **profiles[name]}, indent=2))


def command_profile_verify(args: argparse.Namespace) -> None:
    name = profile_name(args.name)
    registry = profile_registry()
    profile = require_registered_profile(name)
    profile["accountFingerprint"] = identity_fingerprint(args.visible_account)
    profile["identityVerifiedAt"] = now_iso()
    profile["updatedAt"] = now_iso()
    registry["profiles"][name] = profile
    atomic_json_write(PROFILES_PATH, registry)
    print(json.dumps({
        "profile": name,
        "chromeProfile": profile["chromeProfile"],
        "identityVerified": True,
        "identityVerifiedAt": profile["identityVerifiedAt"],
    }, indent=2))


def command_profile_check(args: argparse.Namespace) -> None:
    name = profile_name(args.name)
    profile = require_registered_profile(name)
    expected = profile.get("accountFingerprint")
    if not expected:
        raise RouterError(f"profile identity has not been verified: {name}", 13)
    matched = hmac.compare_digest(expected, identity_fingerprint(args.visible_account))
    print(json.dumps({"profile": name, "identityMatch": matched}, indent=2))
    if not matched:
        raise SystemExit(14)


def live_policy_payload() -> dict:
    return {
        "profileChoices": {"1": "AURUM", "2": "OLATHEDEV"},
        "normalMode": {
            "slashCommand": "/autopilot-on",
            "budgetTokens": str(DEFAULT_MISSION_BUDGET),
            "renewal": "PAUSE_AND_ASK",
        },
        "overnightMode": {
            "slashCommand": "/overnight",
            "missionBudgetTokens": str(OVERNIGHT_MISSION_BUDGET),
            "ttlHours": 6,
            "initialWorkingEnvelopeTokens": str(INITIAL_WORKING_ENVELOPE),
            "renewalTrancheTokens": str(RENEWAL_TRANCHE),
            "protectedCloseoutReserveTokens": str(PROTECTED_CLOSEOUT_RESERVE),
            "conditionalCloseoutExtensionTokens": str(MAX_CLOSEOUT_EXTENSION),
            "absoluteMissionCeilingTokens": str(MAX_MISSION_BUDGET),
            "minimumCloseoutConfidence": str(MIN_CLOSEOUT_CONFIDENCE),
        },
        "deactivateCommand": "/autopilot-off",
        "goldDripRateTokensPerHour": {
            "planningValue": str(USER_REPORTED_GOLD_DRIP_RATE),
            "source": "user-reported; verify from the live balance surface each mission",
            "isHourlySpendQuota": False,
        },
        "literalUnlimitedBudgetAllowed": False,
        "localEfficiency": {
            "localFloorBeforePaidRetry": True,
            "reuseEvidenceOnlyWhenDependencyHashesAreUnchanged": True,
            "rerunOnlyAffectedChecksBeforeTheRequiredCoupledFinalGate": True,
            "platformProbesAreForLiveInformationNotBlindIteration": True,
        },
        "scopeGateRequiredBeforeAutoReview": True,
        "verifierCompletenessAudit": "SKIP",
        "precheckWarningAllowlist": [
            "Problem Description Contains Only Necessary Information",
            "Dockerfile Guidelines",
        ],
        "testFairnessBulbs": {"advisoryMaximum": 4, "investigateAt": 5},
        "preBatchAutoReview": {"maximumAttempts": 3, "success": "APPROVED"},
        "agentRuns": {
            "solver": "Nova",
            "forbiddenSolvers": ["Orion", "Vega"],
            "initialCount": 5,
            "standardTotal": 10,
            "extraNearMissCount": 3,
            "majorityNewTestFailureStopAbove": 6,
        },
        "platformInstability": {"pauseAfterConsecutiveCouldNotCompleteAbove": 5},
        "terminalOrder": ["FP", "solvability", "post-batch Auto Review"],
    }


def command_policy(_: argparse.Namespace) -> None:
    print(json.dumps(live_policy_payload(), indent=2, sort_keys=True))


def command_profile_list(_: argparse.Namespace) -> None:
    print(json.dumps(profile_registry(), indent=2, sort_keys=True))


def command_profile_cli(args: argparse.Namespace) -> None:
    name = profile_name(args.name)
    profile = require_registered_profile(name)
    if not CLI_ENTRY.is_file() or not PRELOAD.is_file():
        raise RouterError("Olympus CLI or profile preload is missing")
    cli_args = list(args.cli_args)
    if cli_args and cli_args[0] == "--":
        cli_args = cli_args[1:]
    if not cli_args:
        raise RouterError("profile cli requires Olympus CLI arguments after --")
    env = os.environ.copy()
    env["OLYMPUS_PROFILE_ROOT"] = profile["cliStateRoot"]
    env["OLYMPUS_NO_UPDATE_CHECK"] = "1"
    completed = subprocess.run(
        ["node", "--import", str(PRELOAD), str(CLI_ENTRY), *cli_args],
        env=env,
        check=False,
    )
    raise SystemExit(completed.returncode)


def command_bind(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    name = profile_name(args.profile)
    require_registered_profile(name)
    url, challenge_id = canonical_submission_url(args.url)
    binding = load_binding(project)
    old_profile = binding.get("profile")
    old_id = binding.get("challengeId")
    if (old_profile or old_id) and not args.replace and (old_profile != name or old_id != challenge_id):
        raise RouterError("project already has a different binding; pass --replace explicitly")
    binding.update({"profile": name, "submissionUrl": url, "challengeId": challenge_id, "lastVerified": None})
    binding["autopilot"] = empty_binding()["autopilot"]
    save_binding(project, binding)
    append_event(project, {"event": "binding-set", "profile": name, "challengeId": challenge_id})
    print(json.dumps(status_payload(project), indent=2))


def command_status(args: argparse.Namespace) -> None:
    print(json.dumps(status_payload(resolve_project(args.project)), indent=2))


def command_require(args: argparse.Namespace) -> None:
    payload = status_payload(resolve_project(args.project))
    print(json.dumps(payload, indent=2))
    missing = payload["missing"]
    if missing == ["profile"]:
        raise SystemExit(10)
    if missing == ["submissionUrl"]:
        raise SystemExit(11)
    if missing:
        raise SystemExit(12)


def command_autopilot_on(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    binding = load_binding(project)
    if not binding.get("profile") or not binding.get("submissionUrl"):
        raise RouterError("project must have both profile and submission URL before autopilot can turn on", 12)
    existing = autopilot_payload(binding)
    if existing.get("enabled") and not autopilot_expired(binding):
        raise RouterError("an autopilot mission is already active; turn it off before starting another", 25)
    mode = args.mode
    maximum_initial_budget = (
        OVERNIGHT_MISSION_BUDGET if mode == "overnight" else DEFAULT_MISSION_BUDGET
    )
    default_budget = maximum_initial_budget
    budget = parse_decimal(args.budget or str(default_budget))
    if budget == 0 or budget > maximum_initial_budget:
        raise RouterError(
            f"{mode} mission budget must be greater than 0 and at most {maximum_initial_budget}"
        )
    ttl = parse_ttl(args.ttl or (DEFAULT_OVERNIGHT_TTL if mode == "overnight" else DEFAULT_NORMAL_TTL))
    if ttl > MAX_MISSION_TTL:
        raise RouterError("the self-work mission TTL is capped at 6h")
    operations = parse_operations(args.allow)
    observed_drip = None
    if args.observed_drip_rate is not None:
        observed_drip = str(parse_decimal(args.observed_drip_rate))
    expires = datetime.now(timezone.utc) + ttl
    mission_id = f"mission-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"
    initial_release = min(INITIAL_WORKING_ENVELOPE, budget)
    reserve = Decimal("0") if mode == "normal" else min(
        PROTECTED_CLOSEOUT_RESERVE, max(Decimal("0"), budget - initial_release)
    )
    binding["autopilot"] = {
        "enabled": True,
        "mode": mode,
        "expiresAt": expires.isoformat().replace("+00:00", "Z"),
        "budgetTokens": str(budget),
        "baseBudgetTokens": str(budget),
        "spentTokens": "0",
        "releasedTokens": str(initial_release),
        "initialWorkingEnvelopeTokens": str(initial_release),
        "renewalTrancheTokens": str(RENEWAL_TRANCHE),
        "protectedReserveTokens": str(reserve),
        "planningDripRateTokensPerHour": str(USER_REPORTED_GOLD_DRIP_RATE),
        "observedDripRateTokensPerHour": observed_drip,
        "closeoutExtensionUsed": False,
        "closeoutEvidenceArtifact": None,
        "allowedOperations": operations,
        "missionId": mission_id,
    }
    binding["workflow"] = empty_binding()["workflow"]
    binding["workflow"]["state"] = "running"
    save_binding(project, binding)
    append_event(project, {
        "event": "autopilot-on",
        "missionId": mission_id,
        "mode": mode,
        "budgetTokens": str(budget),
        "releasedTokens": str(initial_release),
        "protectedReserveTokens": str(reserve),
        "observedDripRateTokensPerHour": observed_drip,
        "allowedOperations": operations,
    })
    print(json.dumps(status_payload(project), indent=2))


def command_autopilot_off(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    binding = load_binding(project)
    autopilot = binding.setdefault("autopilot", empty_binding()["autopilot"])
    previous_mission = autopilot.get("missionId")
    autopilot["enabled"] = False
    autopilot["expiresAt"] = None
    save_binding(project, binding)
    append_event(project, {"event": "autopilot-off", "missionId": previous_mission})
    print(json.dumps(status_payload(project), indent=2))


def command_autopilot_release(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    binding = load_binding(project)
    autopilot = autopilot_payload(binding)
    if not autopilot.get("enabled") or autopilot_expired(binding):
        raise RouterError("autopilot is off or expired; tranche release denied", 20)
    if autopilot.get("mode") != "overnight":
        raise RouterError("normal autopilot stops at 50 tokens and must ask the user for more")
    evidence_path, evidence, digest = project_json_artifact(project, args.evidence)
    mission_id = autopilot.get("missionId")
    if evidence.get("missionId") != mission_id:
        raise RouterError("tranche evidence belongs to a different mission")
    if evidence_digest_used(project, mission_id, "working-envelope-released", digest):
        raise RouterError("this tranche evidence was already used")
    evidence_paths = evidence.get("evidencePaths")
    if not isinstance(evidence_paths, list) or not evidence_paths:
        raise RouterError("tranche evidence requires a nonempty evidencePaths list")
    resolved_evidence = [str(artifact_within_project(project, item)) for item in evidence_paths]
    new_evidence = evidence.get("newEvidence")
    if not isinstance(new_evidence, list) or not new_evidence or not all(
        isinstance(item, str) and item.strip() for item in new_evidence
    ):
        raise RouterError("tranche evidence requires nonempty newEvidence statements")
    if evidence.get("noUnknown") is not True or evidence.get("noBlockingFinding") is not True:
        raise RouterError("tranche release requires noUnknown=true and noBlockingFinding=true")
    operation = evidence.get("nextOperation")
    if operation not in ALL_OPERATIONS or operation == "observe":
        raise RouterError("tranche evidence must name a paid or mutating nextOperation")
    if operation not in set(autopilot.get("allowedOperations") or []):
        raise RouterError(f"next operation is not allowed by this mission: {operation}")
    next_phase = workflow_payload(binding).get("nextPhase")
    expected_phases = OPERATION_PHASES.get(operation)
    if expected_phases and next_phase not in expected_phases:
        raise RouterError(f"next operation {operation} does not match workflow phase {next_phase}")
    next_cost = parse_decimal(str(evidence.get("nextCostTokens", "")))
    if next_cost == 0:
        raise RouterError("tranche evidence nextCostTokens must be greater than zero")
    current_limit = effective_spend_limit(binding)
    spent = parse_decimal(str(autopilot.get("spentTokens", "0")))
    target_limit = spent + next_cost
    if target_limit <= current_limit:
        raise RouterError("the current working envelope already covers the evidenced next operation")
    budget = parse_decimal(str(autopilot.get("budgetTokens", "0")))
    reserve = parse_decimal(str(autopilot.get("protectedReserveTokens", "0")))
    maximum_precloseout_release = max(Decimal("0"), budget - reserve)
    released = parse_decimal(str(autopilot.get("releasedTokens", "0")))
    tranche = parse_decimal(str(autopilot.get("renewalTrancheTokens", RENEWAL_TRANCHE)))
    tranche_count = ((target_limit - current_limit) / tranche).to_integral_value(rounding=ROUND_CEILING)
    new_release = min(maximum_precloseout_release, released + tranche_count * tranche)
    if new_release < target_limit:
        raise RouterError(
            "the evidenced operation would consume the protected closeout reserve or exceed the mission cap"
        )
    binding["autopilot"]["releasedTokens"] = str(new_release)
    save_binding(project, binding)
    append_event(project, {
        "event": "working-envelope-released",
        "missionId": mission_id,
        "evidenceArtifact": str(evidence_path),
        "evidenceSha256": digest,
        "evidencePaths": resolved_evidence,
        "nextOperation": operation,
        "nextCostTokens": str(next_cost),
        "releasedTokens": str(new_release),
    })
    print(json.dumps({
        "released": True,
        "missionId": mission_id,
        "releasedTokens": str(new_release),
        "protectedReserveTokens": str(reserve),
        "evidenceSha256": digest,
    }, indent=2))


def command_autopilot_closeout_extend(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    binding = load_binding(project)
    autopilot = autopilot_payload(binding)
    if not autopilot.get("enabled") or autopilot_expired(binding):
        raise RouterError("autopilot is off or expired; closeout extension denied", 20)
    if autopilot.get("mode") != "overnight":
        raise RouterError("the conditional closeout extension is available only in /overnight mode")
    if autopilot.get("closeoutExtensionUsed"):
        raise RouterError("the one conditional closeout extension was already used")
    if not mission_completed_phase(binding, "post-batch-triad"):
        raise RouterError("closeout extension requires a completed current-mission post-batch triad")
    evidence_path, evidence, digest = project_json_artifact(project, args.evidence)
    mission_id = autopilot.get("missionId")
    if evidence.get("missionId") != mission_id:
        raise RouterError("closeout evidence belongs to a different mission")
    if evidence_digest_used(project, mission_id, "closeout-budget-extended", digest):
        raise RouterError("this closeout evidence was already used")
    if evidence.get("classification") != "minor-closeout":
        raise RouterError("closeout evidence classification must be minor-closeout")
    confidence = parse_decimal(str(evidence.get("confidence", "")))
    if confidence < MIN_CLOSEOUT_CONFIDENCE or confidence > 1:
        raise RouterError(f"closeout confidence must be between {MIN_CLOSEOUT_CONFIDENCE} and 1")
    if evidence.get("requiresRedesign") is not False:
        raise RouterError("closeout extension is forbidden when redesign is required")
    if evidence.get("platformInstability") is not False:
        raise RouterError("closeout extension is forbidden during platform instability")
    if evidence.get("unknowns") != []:
        raise RouterError("closeout extension requires an empty unknowns list")
    if evidence.get("approvalState") not in {
        "NOT_APPROVED", "REVISION_REQUESTED", "PENDING_FINAL_RERUN",
    }:
        raise RouterError("closeout evidence must name the unresolved final approval state")
    genuine_passers = evidence.get("genuinePassers")
    if not isinstance(genuine_passers, int) or genuine_passers < 1:
        raise RouterError("closeout extension requires at least one FP-genuine passer")
    if evidence.get("fpOpen") != 0 or evidence.get("fpBug") != 0:
        raise RouterError("closeout extension requires 0 FP OPEN and 0 FP BUG")
    blockers = evidence.get("blockingFindings")
    if not isinstance(blockers, list) or not 1 <= len(blockers) <= 2:
        raise RouterError("closeout extension requires one or two blockingFindings")
    evidence_paths: list[str] = []
    for blocker in blockers:
        if not isinstance(blocker, dict) or blocker.get("severity") != "minor":
            raise RouterError("every closeout blocking finding must be classified minor")
        if not isinstance(blocker.get("id"), str) or not blocker["id"].strip():
            raise RouterError("every closeout blocking finding requires an id")
        evidence_paths.append(str(artifact_within_project(project, blocker.get("evidencePath", ""))))
    actions = evidence.get("remainingActions")
    if not isinstance(actions, list) or not actions:
        raise RouterError("closeout extension requires a nonempty remainingActions list")
    remaining_cost = Decimal("0")
    allowed = set(autopilot.get("allowedOperations") or [])
    for action in actions:
        if not isinstance(action, dict) or action.get("operation") not in allowed:
            raise RouterError("every closeout action must name an allowed mission operation")
        remaining_cost += parse_decimal(str(action.get("costTokens", "")))
        evidence_paths.append(str(artifact_within_project(project, action.get("evidencePath", ""))))
    current_budget = parse_decimal(str(autopilot.get("budgetTokens", "0")))
    new_budget = parse_decimal(args.new_budget)
    if new_budget < Decimal("200") or new_budget > MAX_MISSION_BUDGET:
        raise RouterError("closeout budget must be between 200 and 250 tokens")
    added = new_budget - current_budget
    if added <= 0 or added > MAX_CLOSEOUT_EXTENSION:
        raise RouterError("closeout extension must add between 1 and 100 tokens")
    if remaining_cost > added:
        raise RouterError(f"remaining action cost exceeds the requested extension: {remaining_cost} > {added}")
    binding["autopilot"]["budgetTokens"] = str(new_budget)
    binding["autopilot"]["closeoutExtensionUsed"] = True
    binding["autopilot"]["closeoutEvidenceArtifact"] = str(evidence_path)
    save_binding(project, binding)
    append_event(project, {
        "event": "closeout-budget-extended",
        "missionId": mission_id,
        "evidenceArtifact": str(evidence_path),
        "evidenceSha256": digest,
        "evidencePaths": evidence_paths,
        "confidence": str(confidence),
        "oldBudgetTokens": str(current_budget),
        "newBudgetTokens": str(new_budget),
        "remainingActionCostTokens": str(remaining_cost),
    })
    print(json.dumps({
        "extended": True,
        "missionId": mission_id,
        "budgetTokens": str(new_budget),
        "absoluteCeilingTokens": str(MAX_MISSION_BUDGET),
        "confidence": str(confidence),
        "evidenceSha256": digest,
    }, indent=2))


def command_can(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    binding = load_binding(project)
    operation = args.operation
    if operation not in ALL_OPERATIONS:
        raise RouterError(f"unknown operation: {operation}")
    cost = parse_decimal(args.cost)
    if operation == "observe" and cost == 0:
        print(json.dumps({"allowed": True, "reason": "read-only observation is allowed while autopilot is off"}))
        return
    autopilot = autopilot_payload(binding)
    if not autopilot.get("enabled") or autopilot_expired(binding):
        raise RouterError("autopilot is off or expired; mutation denied", 20)
    if operation not in set(autopilot.get("allowedOperations") or []):
        raise RouterError(f"operation is not allowed by this mission: {operation}", 21)
    expected_phases = OPERATION_PHASES.get(operation)
    if expected_phases:
        workflow = workflow_payload(binding)
        next_phase = workflow.get("nextPhase")
        if next_phase not in expected_phases:
            raise RouterError(
                f"operation {operation} is out of order: next phase is {next_phase}",
                23,
            )
        if (
            operation == "auto-review"
            and next_phase == "pre-batch-auto-review"
            and operation_count(project, autopilot.get("missionId"), operation, next_phase) >= 3
        ):
            raise RouterError("pre-batch Auto Review is capped at three attempts", 24)
    budget = parse_decimal(str(autopilot.get("budgetTokens", "0")))
    spent = parse_decimal(str(autopilot.get("spentTokens", "0")))
    if spent + cost > budget:
        raise RouterError(f"operation would exceed budget: {spent} + {cost} > {budget}", 22)
    spend_limit = effective_spend_limit(binding)
    if spent + cost > spend_limit:
        raise RouterError(
            f"operation would exceed the released working envelope: {spent} + {cost} > {spend_limit}; "
            "release the smallest evidence-backed tranche or reach the closeout phase",
            26,
        )
    live_balance = None
    if cost > 0:
        if args.live_balance is None:
            raise RouterError("a paid operation requires --live-balance from the current platform surface", 27)
        live_balance = parse_decimal(args.live_balance)
        if cost > live_balance:
            raise RouterError(f"live balance is insufficient for this operation: {cost} > {live_balance}", 28)
    print(json.dumps({
        "allowed": True,
        "operation": operation,
        "cost": str(cost),
        "liveBalance": str(live_balance) if live_balance is not None else None,
        "releasedSpendLimit": str(spend_limit),
        "remainingMissionAfter": str(budget - spent - cost),
        "remainingEnvelopeAfter": str(spend_limit - spent - cost),
        "missionId": autopilot.get("missionId"),
    }))


def command_record(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    binding = load_binding(project)
    cost = parse_decimal(args.cost)
    if cost > 0 and not args.receipt:
        raise RouterError("a paid operation requires a persisted server receipt or job ID")
    command_can(argparse.Namespace(
        project=str(project), operation=args.operation, cost=args.cost,
        live_balance=args.live_balance,
    ))
    autopilot = binding["autopilot"]
    phase = workflow_payload(binding).get("nextPhase")
    spent = parse_decimal(str(autopilot.get("spentTokens", "0"))) + cost
    autopilot["spentTokens"] = str(spent)
    save_binding(project, binding)
    append_event(project, {
        "event": "operation-recorded",
        "operation": args.operation,
        "phase": phase,
        "cost": str(cost),
        "liveBalanceBefore": args.live_balance,
        "receipt": args.receipt,
        "missionId": autopilot.get("missionId"),
    })
    print(json.dumps({"recorded": True, "spentTokens": str(spent), "receipt": args.receipt}))


def command_workflow_status(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    print(json.dumps(workflow_payload(load_binding(project)), indent=2))


def command_workflow_complete(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    binding = load_binding(project)
    autopilot = binding.get("autopilot") or {}
    if not autopilot.get("enabled") or autopilot_expired(binding):
        raise RouterError("autopilot is off or expired; phase completion denied", 20)
    workflow = binding.setdefault("workflow", empty_binding()["workflow"])
    index = int(workflow.get("nextPhaseIndex", 0))
    expected = WORKFLOW_PHASES[index] if index < len(WORKFLOW_PHASES) else None
    if args.phase != expected:
        raise RouterError(f"phase is out of order: expected {expected}, got {args.phase}", 23)
    artifact = artifact_within_project(project, args.artifact)
    if args.phase in RECEIPT_PHASES and not args.receipt:
        raise RouterError(f"phase {args.phase} requires a persisted server receipt/job id")
    phase_operation = PHASE_OPERATION.get(args.phase)
    if phase_operation and not receipt_is_recorded(
        project, autopilot.get("missionId"), phase_operation, args.receipt
    ):
        raise RouterError(
            f"phase receipt is not present in the mission ledger for operation {phase_operation}"
        )
    if args.phase == "consensus" and not args.result:
        raise RouterError("consensus phase requires --result READY or NOT_READY")
    entry = {
        "phase": args.phase,
        "completedAt": now_iso(),
        "artifact": str(artifact),
        "receipt": args.receipt,
        "result": args.result,
        "missionId": autopilot.get("missionId"),
    }
    workflow.setdefault("history", []).append(entry)
    workflow["nextPhaseIndex"] = index + 1
    if args.phase == "consensus":
        workflow["result"] = args.result
        workflow["state"] = "complete" if args.result == "READY" else "not-ready"
    else:
        workflow["state"] = "running"
    save_binding(project, binding)
    append_event(project, {"event": "workflow-phase-complete", **entry})
    print(json.dumps(workflow_payload(binding), indent=2))


def command_workflow_reset(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    binding = load_binding(project)
    autopilot = binding.get("autopilot") or {}
    if not autopilot.get("enabled") or autopilot_expired(binding):
        raise RouterError("autopilot is off or expired; workflow reset denied", 20)
    target = WORKFLOW_PHASES.index(args.to)
    workflow = binding.setdefault("workflow", empty_binding()["workflow"])
    current = int(workflow.get("nextPhaseIndex", 0))
    if target > current:
        raise RouterError("workflow reset cannot skip forward")
    workflow["nextPhaseIndex"] = target
    workflow["state"] = "running"
    workflow["result"] = None
    event = {
        "event": "workflow-reset",
        "to": args.to,
        "reason": args.reason,
        "missionId": autopilot.get("missionId"),
    }
    workflow.setdefault("history", []).append({"resetAt": now_iso(), **event})
    save_binding(project, binding)
    append_event(project, event)
    print(json.dumps(workflow_payload(binding), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="olympus-router")
    sub = parser.add_subparsers(dest="command", required=True)

    profile = sub.add_parser("profile")
    profile_sub = profile.add_subparsers(dest="profile_command", required=True)
    add = profile_sub.add_parser("add")
    add.add_argument("--name", required=True)
    add.add_argument("--chrome-profile", required=True)
    add.set_defaults(func=command_profile_add)
    listing = profile_sub.add_parser("list")
    listing.set_defaults(func=command_profile_list)
    verify = profile_sub.add_parser("verify")
    verify.add_argument("--name", required=True)
    verify.add_argument("--visible-account", required=True)
    verify.set_defaults(func=command_profile_verify)
    check = profile_sub.add_parser("check")
    check.add_argument("--name", required=True)
    check.add_argument("--visible-account", required=True)
    check.set_defaults(func=command_profile_check)
    cli = profile_sub.add_parser("cli")
    cli.add_argument("--name", required=True)
    cli.add_argument("cli_args", nargs=argparse.REMAINDER)
    cli.set_defaults(func=command_profile_cli)

    policy = sub.add_parser("policy")
    policy.set_defaults(func=command_policy)

    bind = sub.add_parser("bind")
    bind.add_argument("--project")
    bind.add_argument("--profile", required=True)
    bind.add_argument("--url", required=True)
    bind.add_argument("--replace", action="store_true")
    bind.set_defaults(func=command_bind)

    for name, func in (("status", command_status), ("require", command_require)):
        item = sub.add_parser(name)
        item.add_argument("--project")
        item.set_defaults(func=func)

    autopilot = sub.add_parser("autopilot")
    autopilot_sub = autopilot.add_subparsers(dest="autopilot_command", required=True)
    on = autopilot_sub.add_parser("on")
    on.add_argument("--project")
    on.add_argument("--mode", choices=("normal", "overnight"), default="normal")
    on.add_argument("--budget")
    on.add_argument("--ttl")
    on.add_argument("--allow", default="standard")
    on.add_argument("--observed-drip-rate")
    on.set_defaults(func=command_autopilot_on)
    off = autopilot_sub.add_parser("off")
    off.add_argument("--project")
    off.set_defaults(func=command_autopilot_off)
    release = autopilot_sub.add_parser("release")
    release.add_argument("--project")
    release.add_argument("--evidence", required=True)
    release.set_defaults(func=command_autopilot_release)
    extend = autopilot_sub.add_parser("closeout-extend")
    extend.add_argument("--project")
    extend.add_argument("--new-budget", required=True)
    extend.add_argument("--evidence", required=True)
    extend.set_defaults(func=command_autopilot_closeout_extend)

    can = sub.add_parser("can")
    can.add_argument("--project")
    can.add_argument("--operation", required=True)
    can.add_argument("--cost", default="0")
    can.add_argument("--live-balance")
    can.set_defaults(func=command_can)

    record = sub.add_parser("record")
    record.add_argument("--project")
    record.add_argument("--operation", required=True)
    record.add_argument("--cost", default="0")
    record.add_argument("--live-balance")
    record.add_argument("--receipt")
    record.set_defaults(func=command_record)

    workflow = sub.add_parser("workflow")
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)
    workflow_status = workflow_sub.add_parser("status")
    workflow_status.add_argument("--project")
    workflow_status.set_defaults(func=command_workflow_status)
    workflow_complete = workflow_sub.add_parser("complete")
    workflow_complete.add_argument("--project")
    workflow_complete.add_argument("--phase", choices=WORKFLOW_PHASES, required=True)
    workflow_complete.add_argument("--artifact", required=True)
    workflow_complete.add_argument("--receipt")
    workflow_complete.add_argument("--result", choices=("READY", "NOT_READY"))
    workflow_complete.set_defaults(func=command_workflow_complete)
    workflow_reset = workflow_sub.add_parser("reset")
    workflow_reset.add_argument("--project")
    workflow_reset.add_argument("--to", choices=WORKFLOW_PHASES, required=True)
    workflow_reset.add_argument("--reason", required=True)
    workflow_reset.set_defaults(func=command_workflow_reset)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        args.func(args)
        return 0
    except RouterError as exc:
        print(json.dumps({"error": str(exc), "exitCode": exc.exit_code}), file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
