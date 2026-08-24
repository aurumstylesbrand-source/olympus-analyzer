#!/Users/mac/olympus-tools/pwenv/bin/python
"""Create or inspect one profile-isolated Shipd browser session.

The user performs sign-in directly in the headed Chrome window. This program
never accepts passwords, cookies, tokens, recovery codes, or OTPs as arguments.
Paid clicks deliberately do not live here: they must pass through the router's
operation/budget/phase checks and be reconciled to a persisted server receipt.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent
ROUTER_SPEC = importlib.util.spec_from_file_location("olympus_router", HERE / "olympus_router.py")
ROUTER = importlib.util.module_from_spec(ROUTER_SPEC)
assert ROUTER_SPEC.loader
ROUTER_SPEC.loader.exec_module(ROUTER)


def registered_profile(name: str) -> dict:
    return ROUTER.require_registered_profile(ROUTER.profile_name(name))


def visible_controls(page) -> list[dict]:
    return page.evaluate(
        """() => [...document.querySelectorAll('button,[role=button],a[href],[role=tab]')]
          .filter((el) => { const r=el.getBoundingClientRect(); return r.width || r.height; })
          .map((el) => ({
            tag: el.tagName.toLowerCase(),
            role: el.getAttribute('role') || '',
            label: (el.innerText || el.getAttribute('aria-label') || '').trim().replace(/\\s+/g,' ').slice(0,160),
            disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true'
          })).filter((x) => x.label)"""
    )


def launch_context(playwright, profile: dict, *, headless: bool):
    state = Path(profile["browserStatePath"])
    browser = playwright.chromium.launch(channel="chrome", headless=headless)
    kwargs = {"viewport": {"width": 1400, "height": 1000}}
    if state.is_file():
        kwargs["storage_state"] = str(state)
    return browser, browser.new_context(**kwargs), state


def login(args: argparse.Namespace) -> int:
    profile = registered_profile(args.profile)
    url, _ = ROUTER.canonical_submission_url(args.url)
    with sync_playwright() as playwright:
        browser, context, state = launch_context(playwright, profile, headless=False)
        page = context.new_page()
        page.set_default_timeout(30_000)
        page.goto(url, wait_until="domcontentloaded")
        print(json.dumps({
            "profile": args.profile,
            "chromeProfileLabel": profile["chromeProfile"],
            "landed": page.url,
            "instruction": "Sign in directly in this Chrome window; no credentials are requested here.",
        }, indent=2), flush=True)
        for _ in range(120):
            page.wait_for_timeout(5_000)
            if "sign-in" not in page.url and len(visible_controls(page)) > 3:
                state.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                context.storage_state(path=str(state))
                state.chmod(0o600)
                print(json.dumps({"signedIn": True, "stateSaved": str(state), "url": page.url}, indent=2))
                browser.close()
                return 0
        print(json.dumps({"signedIn": False, "reason": "timed out waiting for direct browser sign-in"}))
        browser.close()
        return 2


def inspect(args: argparse.Namespace) -> int:
    profile = registered_profile(args.profile)
    url, challenge_id = ROUTER.canonical_submission_url(args.url)
    state = Path(profile["browserStatePath"])
    if not state.is_file():
        print(json.dumps({"error": "browser session is not signed in", "profile": args.profile}), file=sys.stderr)
        return 10
    with sync_playwright() as playwright:
        browser, context, _ = launch_context(playwright, profile, headless=True)
        page = context.new_page()
        page.set_default_timeout(30_000)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(7_000)
        text = page.locator("body").inner_text()
        balances = sorted(set(re.findall(r"\b\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?\b", text)))
        payload = {
            "profile": args.profile,
            "chromeProfileLabel": profile["chromeProfile"],
            "challengeId": challenge_id,
            "requestedUrl": url,
            "landedUrl": page.url,
            "title": page.title(),
            "signedIn": "sign-in" not in page.url,
            "balanceCandidates": balances,
            "controls": visible_controls(page),
        }
        print(json.dumps(payload, indent=2))
        browser.close()
        if payload["landedUrl"].rstrip("/") != url or not payload["signedIn"]:
            return 11
        return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    sub = root.add_subparsers(dest="command", required=True)
    for name, func in (("login", login), ("inspect", inspect)):
        item = sub.add_parser(name)
        item.add_argument("--profile", required=True)
        item.add_argument("--url", required=True)
        item.set_defaults(func=func)
    return root


if __name__ == "__main__":
    options = parser().parse_args()
    raise SystemExit(options.func(options))
