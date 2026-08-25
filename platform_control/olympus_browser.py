#!/usr/bin/env python3
"""Fail-closed boundary for Olympus browser-profile setup.

Browser interaction is performed through the user's connected Chrome surface.
This helper never launches another browser and never reads or exports cookies,
local storage, passwords, profile files, recovery codes, or OTPs.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROUTER_SPEC = importlib.util.spec_from_file_location("olympus_router", HERE / "olympus_router.py")
ROUTER = importlib.util.module_from_spec(ROUTER_SPEC)
assert ROUTER_SPEC.loader
ROUTER_SPEC.loader.exec_module(ROUTER)


def prepare(args: argparse.Namespace) -> int:
    name = ROUTER.profile_name(args.profile)
    profile = ROUTER.require_registered_profile(name)
    print(json.dumps({
        "profile": name,
        "chromeProfile": profile["chromeProfile"],
        "aliases": profile.get("aliases", []),
        "browserMode": "connected-chrome",
        "identityVerified": bool(profile.get("accountFingerprint")),
        "instruction": (
            "Open this named Chrome profile, connect it through Settings -> Computer use, "
            "and sign in directly. The agent must verify the visible Shipd identity read-only."
        ),
        "forbidden": [
            "cookie export",
            "storage-state export",
            "password collection",
            "session-token collection",
            "OTP or recovery-code collection",
        ],
    }, indent=2))
    return 0


def policy(_: argparse.Namespace) -> int:
    print(json.dumps(ROUTER.live_policy_payload(), indent=2, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="olympus-browser")
    sub = root.add_subparsers(dest="command", required=True)
    ready = sub.add_parser("prepare")
    ready.add_argument("--profile", required=True)
    ready.set_defaults(func=prepare)
    rules = sub.add_parser("policy")
    rules.set_defaults(func=policy)
    return root


if __name__ == "__main__":
    options = parser().parse_args()
    raise SystemExit(options.func(options))
