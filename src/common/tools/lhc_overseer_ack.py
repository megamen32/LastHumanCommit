#!/usr/bin/env python3
"""The Overseer review clock of an active plan: due check for the hooks, and the one-command mark.

A hook cannot start an agent. It can only tell the Lead that an Overseer review is due (Stop blocks
once per 30-minute boundary, PostToolUse adds a reminder once per boundary). The Lead calls the
Overseer (zero-knowledge, read-only), then marks the review done with one command, which restarts
the 30 minutes:

    python3 lhc_overseer_ack.py [--plan PLAN_DIR]     mark the review done now
    python3 lhc_overseer_ack.py --self [--plan DIR]   the Lead did the review itself (subagents off)
    python3 lhc_overseer_ack.py --off [--plan DIR]    the owner said no-LHC/STOP: stop reminding
    python3 lhc_overseer_ack.py --status [--plan DIR]

The state is a small file under XDG_STATE_HOME (lhc/overseer), never the repository. A hook that
cannot read or write it stays silent. LHC_OVERSEER=off switches the hook off for a process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

EVERY = 1800  # seconds between Overseer reviews of an active plan
OFF_VALUES = {"0", "off", "no", "false", "stop"}


def state_file(plan):
    plan = Path(plan).resolve()
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "lhc" / "overseer"
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", plan.name)[:60]
    return base / f"{name}-{hashlib.sha1(str(plan).encode()).hexdigest()[:12]}.json"


def read_state(plan):
    try:
        data = json.loads(state_file(plan).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_state(plan, data):
    path = state_file(plan)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        return False
    return True


def disabled(plan):
    if os.environ.get("LHC_OVERSEER", "").strip().lower() in OFF_VALUES:
        return True
    return bool(read_state(plan).get("off"))


def ack(plan, now=None, by="overseer"):
    now = now or time.time()
    data = read_state(plan)
    data.update(last_review=now, since=data.get("since") or now, stop_mark=None, post_mark=None, by=by)
    return write_state(plan, data)


def due(plan, channel, now=None):
    """Minutes since the last review when a review is due and this channel has not yet said so for
    this 30-minute boundary; otherwise None. The first sight of a plan only starts its clock."""
    now = now or time.time()
    if disabled(plan):
        return None
    data = read_state(plan)
    anchor = data.get("last_review") or data.get("since")
    try:
        anchor = float(anchor)
    except (TypeError, ValueError):
        write_state(plan, {**data, "since": now})
        return None
    elapsed = now - anchor
    if elapsed < EVERY:
        return None
    mark = [anchor, int(elapsed // EVERY)]
    if data.get(channel + "_mark") == mark:
        return None  # said once for this boundary; never loops
    data[channel + "_mark"] = mark
    if not write_state(plan, data):
        return None  # without a mark the hook would repeat: stay silent
    return int(elapsed // 60)


def request_text(plan, minutes, self_review=False):
    tool = Path(__file__).resolve()
    if self_review:
        return (f"LHC: plan {Path(plan).name} has been active for {minutes} min without an Overseer review "
                "(one is due every 30 min). Subagents are off, so review it yourself: read the checklist in "
                "agents/Overseer.md, compare the plan with the original owner request and its latest corrections, "
                "write 3 lines in the plan's revisions, then run "
                f"python3 {tool} --self --plan {plan} and finish. Skip it only when the owner said no-LHC or "
                f"STOP (python3 {tool} --off --plan {plan}).")
    return (f"LHC: plan {Path(plan).name} has been active for {minutes} min without an Overseer review "
            "(one is due every 30 min). Call the Overseer now (zero-knowledge, read-only): give it the "
            "original owner request, the owner's latest corrections and the current plan report, not the "
            f"implementation history. Then mark it done with python3 {tool} --plan {plan} and finish. "
            "Act on its RECOMMENDATION or reject it with a concrete observed fact. Skip it only when "
            f"the owner said no-LHC or STOP (python3 {tool} --off --plan {plan}).")


def open_plans(base):
    found = []
    for marker in sorted(Path(base).glob(".agents/tasks/*/plan.json")):
        for leaf in (marker.parent / "leaves").glob("*.json"):
            try:
                status = json.loads(leaf.read_text(encoding="utf-8")).get("status")
            except (OSError, ValueError, AttributeError):
                continue
            if status in ("queued", "running"):
                found.append(marker.parent)
                break
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", type=Path, default=None, help="plan directory; default: the only open plan here")
    parser.add_argument("--off", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--self", dest="self_review", action="store_true",
                        help="the Lead reviewed the plan itself (subagents off)")
    args = parser.parse_args(argv)
    plan = args.plan
    if plan is None:
        plans = open_plans(Path.cwd())
        if len(plans) != 1:
            print("overseer: name the plan with --plan DIR (found %d open plans here)" % len(plans), file=sys.stderr)
            return 1
        plan = plans[0]
    plan = plan.resolve()
    if args.status:
        data = read_state(plan)
        print(json.dumps({"plan": str(plan), "off": bool(data.get("off")), "last_review": data.get("last_review"),
                          "since": data.get("since")}))
        return 0
    if args.off:
        ok = write_state(plan, {**read_state(plan), "off": True})
        print("overseer reminders off for " + plan.name if ok else "overseer: could not write state")
        return 0 if ok else 1
    ok = ack(plan, by="self" if args.self_review else "overseer")
    print("overseer review recorded for " + plan.name if ok else "overseer: could not write state")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
