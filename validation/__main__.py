#!/usr/bin/env python3
"""Run the entire independent R1 validation suite; no quick/sampled mode.

Run from the repository root:

    python3 -u -m validation > artifacts/validation/latest.log 2>&1

Failures use explicit checks, so Python optimization cannot disable them.
The printed hashes bind this run to the exact delivered source/specification.
No scores, tree sizes, or branch counts are calculated for reporting.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hunl_r1 import kernel

from . import betting, cards


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def artifact_checks() -> None:
    base = Path(__file__).resolve().parents[1]
    stored = json.loads((base / "data/preflop-tree.json").read_text(encoding="utf-8"))
    require(stored == kernel.preflop_tree(), "stored preflop JSON differs from kernel")
    text = (base / "docs/r1-game-specification.md").read_text(encoding="utf-8")
    require("R1" in text, "specification version missing")
    result = kernel.demo()
    require(result["status"] == "PASS" and result["mode"] == "showdown",
            "complete integrated demo failed")
    print("PASS: delivered preflop JSON matches the kernel's full preflop expansion", flush=True)
    print("PASS: standalone exact-card kernel completes an integrated hand", flush=True)


def main() -> int:
    base = Path(__file__).resolve().parents[1]
    print("R1 INDEPENDENT VALIDATION — ACTUAL EXECUTION", flush=True)
    print("started_utc=" + stamp(), flush=True)
    print("started_Asia_Seoul=" + datetime.now(timezone(timedelta(hours=9))).isoformat(), flush=True)
    print("python=" + platform.python_version(), flush=True)
    print("optimization=" + str(sys.flags.optimize), flush=True)
    print("command=" + json.dumps(getattr(sys, "orig_argv", [sys.executable] + sys.argv)), flush=True)
    for name in ("docs/r1-game-specification.md", "data/preflop-tree.json",
                 "hunl_r1/__init__.py", "hunl_r1/__main__.py", "hunl_r1/kernel.py",
                 "validation/__init__.py", "validation/__main__.py",
                 "validation/betting.py", "validation/cards.py"):
        print("sha256 " + name + " " + hashlib.sha256((base / name).read_bytes()).hexdigest(), flush=True)
    print("scope=oracle-reachable public/control closure; exact-card support and probability checks; "
          "all physical five-card evaluations; all rank/flush semantic cases for five through seven "
          "cards; full-history information-set and payoff checks", flush=True)
    print("coverage=finite public-state proof reuse plus exact-card induction; no literal enumeration "
          "of all card-labelled complete histories", flush=True)
    try:
        betting.run()
        cards.run()
        artifact_checks()
    except Exception:
        print("FAIL: independent validation", flush=True)
        traceback.print_exc(file=sys.stdout)
        print("finished_utc=" + stamp(), flush=True)
        print("RESULT=FAIL", flush=True)
        return 1
    print("finished_utc=" + stamp(), flush=True)
    print("RESULT=PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
