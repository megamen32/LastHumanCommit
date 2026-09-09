"""Local clock-logic regressions plus a real, separate-process CLI canary."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "src/common/tools/lhc_active_time.py"
spec = importlib.util.spec_from_file_location("active_time", TOOL)
timer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timer)


def sample(mono, wall=1000, boot="boot-a"):
    return {"monotonic_ns": mono * 1_000_000_000, "wall_ns": wall * 1_000_000_000,
            "boot": {"id": boot, "source": "test-only", "limitations": []}}


class ActiveTimeTest(unittest.TestCase):
    def start(self):
        return timer.transition(None, "start", sample(10), "lead", "task")

    def test_paused_time_excluded(self):
        state = timer.transition(self.start(), "pause", sample(15, 1005))
        state = timer.transition(state, "resume", sample(115, 1105))
        state = timer.transition(state, "stop", sample(118, 1108))
        report = timer.report(state, sample(200, 1200))
        self.assertEqual(report["measured_active_seconds"], 8)
        self.assertEqual(report["wall_seconds"], 108)
        self.assertFalse(report["measurement_still_open"])

    def test_open_interval_disclosed(self):
        result = timer.report(self.start(), sample(17, 1007))
        self.assertEqual(result["finalized_active_seconds"], 0)
        self.assertEqual(result["open_interval_seconds"], 7)
        self.assertTrue(result["measurement_still_open"])
        self.assertIn("crash", " ".join(result["coverage_limitations"]))

    def test_invalid_transitions(self):
        running = self.start()
        paused = timer.transition(running, "pause", sample(15))
        stopped = timer.transition(paused, "stop", sample(20))
        for state, command in [(None, "pause"), (running, "start"),
                               (running, "resume"), (paused, "pause"),
                               (stopped, "start"), (stopped, "stop")]:
            with self.subTest(command=command, state=state):
                with self.assertRaises(ValueError):
                    timer.transition(state, command, sample(25))

    def test_resume_stopped_preserves_totals_and_excludes_stopped_gap(self):
        state = timer.transition(self.start(), "stop", sample(15, 1005))
        state = timer.transition(state, "resume", sample(115, 1105))
        self.assertIsNone(state["stopped"])
        self.assertEqual(state["active_ns"], 5_000_000_000)
        self.assertEqual(state["started"], sample(10))
        self.assertEqual(state["status"], "running")
        self.assertTrue(timer.report(state, sample(115, 1105))["measurement_still_open"])
        state = timer.transition(state, "stop", sample(118, 1108))
        result = timer.report(state, sample(200, 1200))
        self.assertEqual(result["measured_active_seconds"], 8)
        self.assertEqual(result["wall_seconds"], 108)

    def test_backward_and_cross_boot_open_rejected(self):
        state = timer.transition(self.start(), "status", sample(20))
        for now in [sample(19), sample(30, boot="boot-b")]:
            for command in ["status", "pause", "stop"]:
                with self.assertRaises(ValueError):
                    timer.transition(state, command, now)

    def test_paused_reboot_can_resume_without_inference(self):
        state = timer.transition(self.start(), "pause", sample(15))
        state = timer.transition(state, "resume", sample(2, 2000, "boot-b"))
        state = timer.transition(state, "stop", sample(5, 2003, "boot-b"))
        self.assertEqual(timer.report(state, sample(5, 2003, "boot-b"))
                         ["measured_active_seconds"], 8)

    def test_wall_clock_is_diagnostic_only(self):
        state = timer.transition(self.start(), "stop", sample(15, 990))
        result = timer.report(state, sample(15, 990))
        self.assertEqual(result["measured_active_seconds"], 5)
        self.assertEqual(result["wall_seconds"], -10)
        self.assertTrue(result["wall_clock_went_backward"])

    def test_boot_fallback_discloses_evidence(self):
        def read(path, **kwargs):
            if str(path) == "/proc/stat":
                return "cpu 1 2 3\nbtime 123456\n"
            raise OSError("unavailable")
        with patch.object(Path, "read_text", read):
            result = timer.boot_identity()
        self.assertIn("btime", result["source"])
        self.assertTrue(result["limitations"])

    def test_unknown_boot_fails_closed(self):
        with patch.object(Path, "read_text", side_effect=OSError), \
                patch.object(timer.sys, "platform", "unknown"):
            with self.assertRaises(ValueError):
                timer.boot_identity()

    def test_atomic_failure_preserves_state(self):
        ROOT.joinpath(".tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".tmp") as folder:
            path = Path(folder) / "state.json"
            timer.atomic_write(path, self.start())
            before = path.read_bytes()
            with patch.object(timer.os, "replace", side_effect=OSError("failure")):
                with self.assertRaises(OSError):
                    timer.atomic_write(path, {"broken": True})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_real_cli_canary(self):
        ROOT.joinpath(".tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".tmp") as folder:
            path = Path(folder) / "timer.json"
            def run(command, ok=True):
                args = [sys.executable, "-B", str(TOOL), command, "--state", str(path)]
                if command == "start":
                    args += ["--actor", "test-lead", "--task", "cli-canary"]
                proc = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0 if ok else 2, proc.stderr)
                return json.loads(proc.stdout)
            run("start")
            imported = timer.status(path)
            self.assertTrue(imported["measurement_still_open"])
            self.assertGreaterEqual(imported["measured_active_seconds"], 0)
            time.sleep(0.03)
            paused = run("pause")
            before = path.read_bytes()
            run("pause", ok=False)
            self.assertEqual(path.read_bytes(), before)
            time.sleep(0.08)
            status = run("status")
            self.assertEqual(status["measured_active_seconds"], paused["measured_active_seconds"])
            run("resume")
            time.sleep(0.03)
            stopped = run("stop")
            self.assertGreater(stopped["measured_active_seconds"], paused["measured_active_seconds"])
            self.assertGreater(stopped["wall_seconds"] - stopped["measured_active_seconds"], 0.08)
            self.assertEqual(run("status")["measured_active_seconds"], stopped["measured_active_seconds"])
            self.assertEqual(timer.status(str(path))["measured_active_seconds"], stopped["measured_active_seconds"])
            before = path.read_bytes()
            run("start", ok=False)
            self.assertEqual(path.read_bytes(), before)
            resumed = run("resume")
            self.assertTrue(resumed["measurement_still_open"])
            self.assertEqual(resumed["finalized_active_seconds"], stopped["measured_active_seconds"])
            time.sleep(0.03)
            restopped = run("stop")
            self.assertGreater(restopped["measured_active_seconds"], stopped["measured_active_seconds"])
            self.assertEqual(restopped["wall_anchor_utc"], stopped["wall_anchor_utc"])
            self.assertEqual(stopped["actor"], "test-lead")
            self.assertIn("monotonic", stopped["source"])
            print("REAL CLI CANARY:", json.dumps(stopped, sort_keys=True))

    def test_importable_status_does_not_start_missing_state(self):
        ROOT.joinpath(".tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".tmp") as folder:
            path = Path(folder) / "missing.json"
            with self.assertRaises(ValueError):
                timer.status(path)
            self.assertFalse(path.exists())

    def test_importable_status_rejects_crossboot_open(self):
        ROOT.joinpath(".tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".tmp") as folder:
            path = Path(folder) / "state.json"
            timer.atomic_write(path, self.start())
            before = path.read_bytes()
            with patch.object(timer, "clock_sample", return_value=sample(50, boot="new-boot")):
                with self.assertRaisesRegex(ValueError, "still-open"):
                    timer.status(path)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
