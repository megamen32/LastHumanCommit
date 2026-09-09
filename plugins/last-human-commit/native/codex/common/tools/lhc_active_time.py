#!/usr/bin/env python3
"""Explicit, dependency-free active-interval ledger (POSIX).

Run: python3 lhc_active_time.py start --state PATH --actor lead --task TASK
Then: pause / resume / status / stop --state PATH. Pause before user waits or
idle; resume when work actually resumes. Choose a separate path per actor/task.
Never backfill time: start has no timestamp override. Stop closes measurement;
explicit resume reopens it with the same owner, wall anchor and accumulated time.
This measures declared elapsed intervals, not CPU usage or inferred activity.
An unclosed/crashed interval remains visibly open; its duration is provisional.

Sibling tools may import status(path): it returns the CLI report dictionary,
including measured_active_seconds, finalized_active_seconds and
measurement_still_open. OSError/ValueError mean unavailable measurement, never
zero. The hook's estimates/idle caps must not be substituted for this ledger.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import uuid


def boot_identity():
    """Prefer a kernel boot UUID; disclose weaker native boot-time evidence."""
    try:
        value = str(uuid.UUID(Path("/proc/sys/kernel/random/boot_id").read_text().strip()))
        return {"id": value, "source": "/proc/sys/kernel/random/boot_id",
                "limitations": []}
    except (OSError, ValueError):
        pass
    try:
        match = re.search(r"^btime (\d+)$", Path("/proc/stat").read_text(), re.M)
        if match:
            return {"id": socket.gethostname() + ":" + match[1],
                    "source": "/proc/stat btime + hostname (fallback)",
                    "limitations": ["Fallback boot time has second resolution; hostname and boot-time collisions are possible."]}
    except OSError:
        pass
    if sys.platform == "darwin":
        try:
            result = subprocess.run(["/usr/sbin/sysctl", "-n", "kern.boottime"],
                                    capture_output=True, text=True, timeout=2, check=True)
            match = re.search(r"sec\s*=\s*(\d+),\s*usec\s*=\s*(\d+)", result.stdout)
            if match:
                return {"id": socket.gethostname() + ":" + ":".join(match.groups()),
                        "source": "sysctl kern.boottime + hostname (fallback)",
                        "limitations": ["Fallback boot identity uses kernel boot time and hostname, not a boot UUID."]}
        except (OSError, subprocess.SubprocessError):
            pass
    raise ValueError("boot identity unavailable; refusing to infer it from wall minus uptime")


def clock_sample():
    boot = boot_identity()
    return {"monotonic_ns": time.monotonic_ns(), "wall_ns": time.time_ns(), "boot": boot}


def same_boot(a, b):
    return a["boot"]["id"] == b["boot"]["id"] and a["boot"]["source"] == b["boot"]["source"]


def check_clock(state, now):
    previous = state["last_sample"]
    if state["status"] == "running" and not same_boot(previous, now):
        raise ValueError("cross-boot or changed boot evidence with still-open interval; duration unknown, state preserved")
    if same_boot(previous, now) and now["monotonic_ns"] < previous["monotonic_ns"]:
        raise ValueError("monotonic clock moved backward; state preserved")


def transition(state, command, now, actor=None, task=None):
    if command == "start":
        if state is not None:
            raise ValueError("state already exists; choose a new actor/task state path")
        if not actor or not actor.strip() or not task or not task.strip():
            raise ValueError("start requires --actor and --task")
        return {"version": 1, "actor": actor, "task": task, "status": "running",
                "started": now, "last_sample": now, "open_monotonic_ns": now["monotonic_ns"],
                "active_ns": 0, "stopped": None, "wall_clock_went_backward": False,
                "boot_evidence": [now["boot"]]}
    if state is None:
        raise ValueError("state does not exist; start explicitly before measuring")
    check_clock(state, now)
    allowed = {"status": {"running", "paused", "stopped"}, "pause": {"running"},
               "resume": {"paused", "stopped"}, "stop": {"running", "paused"}}
    if state["status"] not in allowed.get(command, set()):
        raise ValueError(f"invalid transition: {state['status']} -> {command}")
    state = copy.deepcopy(state)
    if state["status"] == "stopped" and command == "status":
        return state
    state["wall_clock_went_backward"] |= now["wall_ns"] < state["last_sample"]["wall_ns"]
    if now["boot"] not in state["boot_evidence"]:
        state["boot_evidence"].append(now["boot"])
    if command in {"pause", "stop"}:
        if state["status"] == "running":
            state["active_ns"] += now["monotonic_ns"] - state["open_monotonic_ns"]
        state["open_monotonic_ns"] = None
        state["status"] = "paused" if command == "pause" else "stopped"
        if command == "stop":
            state["stopped"] = now
    elif command == "resume":
        state["stopped"] = None
        state["open_monotonic_ns"] = now["monotonic_ns"]
        state["status"] = "running"
    state["last_sample"] = now
    return state


def report(state, now):
    check_clock(state, now)
    open_ns = now["monotonic_ns"] - state["open_monotonic_ns"] if state["status"] == "running" else 0
    end = state["stopped"] or now
    limitations = [
        "Measures explicitly declared elapsed work intervals, not CPU time or verified human/agent activity.",
        "Operator must pause before user idle/waits; no automatic idle or crash detection.",
        "Still-open measurement is provisional and may include time after a crash or forgotten pause; unknown activity is never reconstructed.",
        "OS monotonic suspend behavior is platform-dependent; pause before suspend.",
        "Wall seconds are a wall-clock anchor diagnostic, subject to clock adjustments; never used for active time.",
    ]
    for boot in state["boot_evidence"]:
        limitations.extend(boot["limitations"])
    return {"actor": state["actor"], "task": state["task"], "status": state["status"],
            "measured_active_seconds": (state["active_ns"] + open_ns) / 1e9,
            "finalized_active_seconds": state["active_ns"] / 1e9,
            "open_interval_seconds": open_ns / 1e9,
            "measurement_still_open": state["status"] == "running",
            "wall_seconds": (end["wall_ns"] - state["started"]["wall_ns"]) / 1e9,
            "wall_anchor_utc": datetime.fromtimestamp(state["started"]["wall_ns"] / 1e9, timezone.utc).isoformat(),
            "wall_clock_went_backward": state["wall_clock_went_backward"],
            "source": "time.monotonic_ns() across explicit CLI calls with same-boot evidence; time.time_ns() wall diagnostic",
            "boot_evidence": state["boot_evidence"], "coverage_limitations": limitations}


def atomic_write(path, state):
    """Replace only a complete, flushed JSON state in the same directory."""
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", delete=False) as output:
            name = output.name
            json.dump(state, output, allow_nan=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def operate(command, state_path, actor=None, task=None):
    """Execute one serialized operation; errors preserve the existing ledger."""
    path = Path(state_path).expanduser().resolve()
    if command == "start":
        path.parent.mkdir(parents=True, exist_ok=True)
    # Stable sidecar inode serializes read-modify-replace across CLI calls.
    with open(str(path) + ".lock", "a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = None
        if path.exists():
            state = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(state, dict) or state.get("version") != 1:
                raise ValueError("invalid or unsupported state; state preserved")
        now = clock_sample()
        try:
            updated = transition(state, command, now, actor, task)
            result = report(updated, now)
        except (KeyError, TypeError) as error:
            raise ValueError("malformed state; state preserved") from error
        if updated != state:
            atomic_write(path, updated)
    return result


def status(state_path):
    """Read live measured seconds and coverage; never start/resume implicitly.

    Returns the same dictionary as CLI status. Check measurement_still_open:
    measured_active_seconds includes that provisional interval, whereas
    finalized_active_seconds includes only explicitly closed intervals.
    Missing, malformed, backward-clock or cross-boot-open state raises
    OSError/ValueError. Importers must report unavailable, not invent a value.
    """
    return operate("status", state_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["start", "pause", "resume", "status", "stop"])
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--actor", help="required on start; persisted owner")
    parser.add_argument("--task", help="required on start; persisted task identity")
    args = parser.parse_args(argv)
    try:
        if args.command != "start" and (args.actor is not None or args.task is not None):
            raise ValueError("--actor and --task are only accepted on start")
        result = operate(args.command, args.state, args.actor, args.task)
        print(json.dumps(result, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {"error": str(error), "state_preserved": True,
                  "measured_active_seconds": None}
        print(json.dumps(result))
        return 2


if __name__ == "__main__":
    sys.exit(main())
