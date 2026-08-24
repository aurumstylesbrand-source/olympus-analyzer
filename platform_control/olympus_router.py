#!/usr/bin/env python3
"""Safe project/account binding and authorization router for Olympus platform work.

This controller stores routing metadata only. Browser cookies remain in Chrome,
and CLI tokens remain in a profile-private CLI state directory.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse


SCHEMA_VERSION = 2
PROFILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
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
    "agent-rollouts",
    "post-batch-triad",
    "post-batch-auto-review",
    "consensus",
)
OPERATION_PHASE = {
    "upload": "upload-readback",
    "prechecks": "prechecks",
    "scope-gate": "scope-gate",
    "quality-check": "quality-checks",
    "rollout": "agent-rollouts",
    "auto-review": "post-batch-auto-review",
}
PHASE_OPERATION = {phase: operation for operation, phase in OPERATION_PHASE.items()}
RECEIPT_PHASES = {
    "upload-readback",
    "prechecks",
    "scope-gate",
    "quality-checks",
    "agent-rollouts",
    "post-batch-auto-review",
}

USER_ROOT = Path("/Users/mac")
CONFIG_ROOT = USER_ROOT / ".config" / "olympus-platform"
STATE_ROOT = USER_ROOT / ".local" / "state" / "olympus-platform"
PROFILE_STATE_ROOT = USER_ROOT / ".local" / "share" / "olympus-platform" / "profiles"
BROWSER_STATE_ROOT = USER_ROOT / ".local" / "share" / "olympus-platform" / "browser"
PROFILES_PATH = CONFIG_ROOT / "profiles.json"
CLI_ENTRY = USER_ROOT / ".npm-global" / "lib" / "node_modules" / "@shipd-ai" / "olympus-cli" / "dist" / "index.js"
PRELOAD = Path(__file__).with_name("olympus_homedir_preload.mjs")


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
    if not PROFILE_RE.fullmatch(value):
        raise RouterError("profile must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    return value


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


def empty_binding() -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "profile": None,
        "submissionUrl": None,
        "challengeId": None,
        "lastVerified": None,
        "autopilot": {
            "enabled": False,
            "expiresAt": None,
            "budgetTokens": "0",
            "spentTokens": "0",
            "allowedOperations": ["observe"],
            "missionId": None,
        },
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


def require_registered_profile(name: str) -> dict:
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


def artifact_within_project(project: Path, value: str) -> Path:
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(project)
    except ValueError as exc:
        raise RouterError("phase artifact must be inside the bound project") from exc
    if not path.is_file() or path.stat().st_size == 0:
        raise RouterError(f"phase artifact must be a nonempty file: {path}")
    return path


def status_payload(project: Path) -> dict:
    binding = load_binding(project)
    missing = []
    if not binding.get("profile"):
        missing.append("profile")
    if not binding.get("submissionUrl"):
        missing.append("submissionUrl")
    autopilot = dict(binding.get("autopilot") or {})
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
    secure_dir(BROWSER_STATE_ROOT)
    profiles[name] = {
        "chromeProfile": args.chrome_profile,
        "cliStateRoot": str(root),
        "browserStatePath": str(BROWSER_STATE_ROOT / f"{name}.json"),
        "createdAt": profiles.get(name, {}).get("createdAt", now_iso()),
        "updatedAt": now_iso(),
    }
    atomic_json_write(PROFILES_PATH, registry)
    print(json.dumps({"registered": name, **profiles[name]}, indent=2))


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
    budget = parse_decimal(args.budget)
    ttl = parse_ttl(args.ttl)
    operations = parse_operations(args.allow)
    expires = datetime.now(timezone.utc) + ttl
    mission_id = f"mission-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    binding["autopilot"] = {
        "enabled": True,
        "expiresAt": expires.isoformat().replace("+00:00", "Z"),
        "budgetTokens": str(budget),
        "spentTokens": "0",
        "allowedOperations": operations,
        "missionId": mission_id,
    }
    binding["workflow"] = empty_binding()["workflow"]
    binding["workflow"]["state"] = "running"
    save_binding(project, binding)
    append_event(project, {"event": "autopilot-on", "missionId": mission_id, "budgetTokens": str(budget), "allowedOperations": operations})
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
    autopilot = binding.get("autopilot") or {}
    if not autopilot.get("enabled") or autopilot_expired(binding):
        raise RouterError("autopilot is off or expired; mutation denied", 20)
    if operation not in set(autopilot.get("allowedOperations") or []):
        raise RouterError(f"operation is not allowed by this mission: {operation}", 21)
    expected_phase = OPERATION_PHASE.get(operation)
    if expected_phase:
        workflow = workflow_payload(binding)
        if workflow.get("nextPhase") != expected_phase:
            raise RouterError(
                f"operation {operation} is out of order: next phase is {workflow.get('nextPhase')}",
                23,
            )
    budget = parse_decimal(str(autopilot.get("budgetTokens", "0")))
    spent = parse_decimal(str(autopilot.get("spentTokens", "0")))
    if spent + cost > budget:
        raise RouterError(f"operation would exceed budget: {spent} + {cost} > {budget}", 22)
    print(json.dumps({"allowed": True, "operation": operation, "cost": str(cost), "remainingAfter": str(budget - spent - cost), "missionId": autopilot.get("missionId")}))


def command_record(args: argparse.Namespace) -> None:
    project = resolve_project(args.project)
    binding = load_binding(project)
    cost = parse_decimal(args.cost)
    if cost > 0 and not args.receipt:
        raise RouterError("a paid operation requires a persisted server receipt or job ID")
    command_can(argparse.Namespace(project=str(project), operation=args.operation, cost=args.cost))
    autopilot = binding["autopilot"]
    spent = parse_decimal(str(autopilot.get("spentTokens", "0"))) + cost
    autopilot["spentTokens"] = str(spent)
    save_binding(project, binding)
    append_event(project, {"event": "operation-recorded", "operation": args.operation, "cost": str(cost), "receipt": args.receipt, "missionId": autopilot.get("missionId")})
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
    cli = profile_sub.add_parser("cli")
    cli.add_argument("--name", required=True)
    cli.add_argument("cli_args", nargs=argparse.REMAINDER)
    cli.set_defaults(func=command_profile_cli)

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
    on.add_argument("--budget", required=True)
    on.add_argument("--ttl", default="2h")
    on.add_argument("--allow", default="standard")
    on.set_defaults(func=command_autopilot_on)
    off = autopilot_sub.add_parser("off")
    off.add_argument("--project")
    off.set_defaults(func=command_autopilot_off)

    can = sub.add_parser("can")
    can.add_argument("--project")
    can.add_argument("--operation", required=True)
    can.add_argument("--cost", default="0")
    can.set_defaults(func=command_can)

    record = sub.add_parser("record")
    record.add_argument("--project")
    record.add_argument("--operation", required=True)
    record.add_argument("--cost", default="0")
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
