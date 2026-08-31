#!/usr/bin/env python3
"""One-shot live smoke test for the Rocket.Chat bridge (no interactive loop).

Reads credentials from the environment (never hard-codes them):
  RC_URL, RC_USER, RC_PASS, RC_DM (your own username for a self-DM).

Steps: login -> open self-DM -> post a marker -> build a real demo answer
(`? пайплайн` as head-of-sales, with the 🤖 summary) and post it -> read the
DM history back and confirm both messages arrived. Prints PASS/FAIL and exits
non-zero on any failure. Run via:  python3 integrations/rocketchat/smoke_test.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "integrations" / "rocketchat")]

import bridge  # noqa: E402


def _need(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"[FAIL] env {name} is not set — run with RC_URL/RC_USER/RC_PASS/RC_DM exported.")
        sys.exit(2)
    return val


def main() -> int:
    url, user, password = _need("RC_URL"), _need("RC_USER"), _need("RC_PASS")
    dm = os.environ.get("RC_DM", "").strip() or user  # self-DM defaults to own username
    ok = True

    print(f"== Rocket.Chat smoke == {url} as {user}, self-DM '{dm}'")
    rc = bridge.RocketChat(url, user, password)

    try:
        rc.login()
        print(f"[PASS] login (userId={rc.user_id[:6]}…)")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] login: {exc}")
        return 1

    try:
        room_id, kind = rc.resolve_dm(dm)
        print(f"[PASS] open self-DM ({kind}/{room_id[:6]}…)")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] open DM '{dm}': {exc}")
        return 1

    marker = f"✅ SalesWiki bridge smoke {bridge.now_iso()}"
    rc.post(room_id, marker)
    print("[PASS] posted marker message")

    # Build a real demo answer through the same path the bridge uses.
    wiki = bridge.Wiki()
    state = {"role": "head-of-sales", "trigger": "?",
             "company_name": "BluePeak Energy", "company_id": "demo-company-bluepeak-energy"}
    answer = bridge.handle("? пайплайн", wiki=wiki, state=state)
    rc.post(room_id, answer)
    print("[PASS] posted a real demo answer (? пайплайн, head-of-sales)")
    if bridge.SUMMARY_MARKER not in answer:
        print("[WARN] answer has no 🤖 summary header")
    else:
        print("[PASS] answer carries the 🤖 summary header")

    # Read the DM history back and confirm both posts are visible.
    msgs = rc.history(kind, room_id, "1970-01-01T00:00:00.000Z")
    texts = [m.get("msg", "") for m in msgs]
    if marker in texts:
        print("[PASS] read marker back from history")
    else:
        print("[FAIL] marker not found in history (read-back failed)"); ok = False
    if any("Pipeline Risk Digest" in t for t in texts):
        print("[PASS] read the demo answer back from history")
    else:
        print("[FAIL] demo answer not found in history"); ok = False

    print("\n" + ("SMOKE PASSED — live round-trip works." if ok else "SMOKE FAILED — see above."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
