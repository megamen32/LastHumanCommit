"""Real CLI interval ledger -> explicit time-guard CLI integration.

The installed hook surface is time-only: it tracks elapsed wall time and points
at the method. The interval ledger and the active-time accounting are driven by
the explicit CLI (``lhc_time_guard.py hook``) that the agent calls by the
method; ``--event UserPromptSubmit`` is the legacy adapter label of that CLI
call, not an installed native hook event.

No patched clocks, subprocesses or services: only the legacy persisted counter
is seeded deliberately to prove that partial intervals never reset total time.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest

from _inprocess_lane import git_repo, run_tool


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "src/common/tools/lhc_time_guard.py"
LEDGER = GUARD.with_name("lhc_active_time.py")


class TimeGuardActiveIntegrationTest(unittest.TestCase):
    def setUp(self):
        (ROOT / ".tmp").mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=ROOT / ".tmp")
        self.addCleanup(self.directory.cleanup)
        self.project = Path(self.directory.name)
        git_repo(self.project)
        self.card = self.project / ".agents/tasks/work-real-active.md"
        self.card.parent.mkdir(parents=True)
        self.started = datetime.now(timezone.utc) - timedelta(seconds=2)
        self.write_card()
        self.session_id = "real-ledger-canary"
        self.ledger = self.ledger_path(self.session_id)
        digest = hashlib.sha256(str(self.card).encode()).hexdigest()[:12]
        self.guard_state = self.ledger.parent / f"{self.card.stem}-{digest}.json"

    def ledger_path(self, session_id):
        digest = hashlib.sha256(session_id.encode()).hexdigest()[:12]
        return (self.project / ".agents/shared-session/time" /
                f"{self.card.stem}-{digest}.active.json")

    def write_card(self, active=None):
        explicit = "" if active is None else f"- Active minutes: {active}\n"
        self.card.write_text(
            "# Real active-time integration canary\n"
            "Status: in progress\n"
            "Latest user request: verify real interval accounting\n"
            "Accepted business outcome / Definition of Done: paused time stays fixed\n"
            f"- Started at: {self.started.isoformat()}\n"
            "- Initial estimate: 5 / 120 active minutes\n" + explicit,
            encoding="utf-8",
        )

    def ledger_command(self, command, actor=None, task=None):
        argv = [command, "--state", str(self.ledger)]
        if command == "start":
            argv += ["--actor", actor or self.session_id, "--task", task or self.card.stem]
        completed = run_tool("lhc_active_time", argv, cwd=self.project)
        completed.check_returncode()
        return json.loads(completed.stdout)

    def hook(self, session_id=None):
        completed = run_tool(
            "lhc_time_guard",
            ["hook", "--runtime", "codex", "--event", "UserPromptSubmit"],
            stdin=json.dumps({"cwd": str(self.project), "session_id": session_id or self.session_id,
                              "hook_event_name": "UserPromptSubmit",
                              "prompt": "Report actual active time and coverage."}),
            cwd=self.project,
        )
        completed.check_returncode()
        self.assertTrue(completed.stdout.strip(), completed.stderr)
        result = json.loads(completed.stdout)["hookSpecificOutput"]
        self.assertEqual(result["hookEventName"], "UserPromptSubmit")
        return result["additionalContext"]

    def active_minutes(self, prompt):
        match = re.search(r"(?:reported|estimated) (\d+) active minutes", prompt)
        self.assertIsNotNone(match, prompt)
        return int(match[1])

    def test_paused_ledger_does_not_reset_card_or_add_legacy_estimate(self):
        self.write_card(active=777)
        self.ledger_command("start")
        time.sleep(0.025)
        paused = self.ledger_command("pause")
        initial = self.hook()
        self.assertIn("Separate measurement source=interval-ledger:", initial)
        self.assertIn("active source=task-card", initial)
        self.assertEqual(self.active_minutes(initial), 777)
        self.assertIn("657", initial, "The original 120-minute maximum must still be exceeded")
        self.assertIn("Did you track it? Answer: unknown.", initial)
        self.assertIn(f"source=interval-ledger: {paused['measured_active_seconds']} seconds", initial)
        # A pre-existing hook estimate can be much larger than the real ledger.
        legacy = json.loads(self.guard_state.read_text())
        legacy["tracked_active_seconds"] = 999 * 60
        self.guard_state.write_text(json.dumps(legacy), encoding="utf-8")
        time.sleep(0.08)
        repeated = self.hook()
        after = self.ledger_command("status")
        self.assertEqual(after["measured_active_seconds"], paused["measured_active_seconds"])
        self.assertEqual(self.active_minutes(repeated), self.active_minutes(initial))
        self.assertIn("Separate measurement source=interval-ledger:", repeated)
        self.assertIn("active source=task-card", repeated)
        self.assertIn("open interval provisional=False", repeated)
        self.assertIn("777 active minutes", repeated)
        self.assertNotIn("999 active minutes", repeated)
        self.assertNotIn("Active interval accounting is missing or unavailable", repeated)
        self.assertEqual(self.card.read_text().count("Active minutes: 777"), 1)
        self.assertIn(f"source=interval-ledger: {paused['measured_active_seconds']} seconds", repeated)
        self.assertEqual(json.loads(self.guard_state.read_text())["last_active_minutes"], 777)

    def test_open_ledger_reports_provisional_time_and_coverage_gap(self):
        opened = self.ledger_command("start")
        prompt = self.hook()
        self.assertIn("Separate measurement source=interval-ledger:", prompt)
        self.assertIn("active source=hook-observed", prompt)
        self.assertIn("open interval provisional=True", prompt)
        self.assertIn(f"coverage begins {opened['wall_anchor_utc']}", prompt)
        self.assertIn("unknown", prompt.lower())
        self.assertIn("do not sum overlapping or unknown intervals", prompt)
        self.assertIn("not CPU time", prompt)
        self.assertIn(str(self.ledger), prompt)
        self.assertIn(f"started {self.started.isoformat()}", prompt)
        self.assertGreater(datetime.fromisoformat(opened["wall_anchor_utc"]), self.started)
        self.ledger_command("stop")

    def test_partial_ledger_preserves_legacy_estimate_for_check(self):
        self.hook()
        legacy = json.loads(self.guard_state.read_text())
        legacy["tracked_active_seconds"] = 125 * 60
        self.guard_state.write_text(json.dumps(legacy), encoding="utf-8")
        self.ledger_command("start")
        self.ledger_command("pause")
        prompt = self.hook()
        self.assertEqual(self.active_minutes(prompt), 125)
        self.assertIn("active source=hook-observed", prompt)
        self.assertIn("Separate measurement source=interval-ledger:", prompt)
        self.assertIn("estimated 125 active minutes", prompt)
        self.assertEqual(json.loads(self.guard_state.read_text())["last_active_minutes"], 125)
        self.assertIn("Did you track it? Answer: unknown.", prompt)

    def assert_repair(self, prompt):
        self.assertIn("Active interval accounting is missing or unavailable", prompt)
        self.assertNotIn("Separate measurement source=interval-ledger:", prompt)
        self.assertIn("active source=hook-observed", prompt)

    def test_stopped_ledger_requires_repair(self):
        self.ledger_command("start")
        stopped = self.ledger_command("stop")
        self.assert_repair(self.hook())
        resumed = self.ledger_command("resume")
        self.assertEqual(resumed["finalized_active_seconds"], stopped["measured_active_seconds"])
        prompt = self.hook()
        self.assertIn("Separate measurement source=interval-ledger:", prompt)
        self.assertNotIn("Active interval accounting is missing or unavailable", prompt)

    def test_foreign_actor_requires_repair(self):
        self.ledger_command("start", actor="another-session")
        self.assert_repair(self.hook())

    def test_foreign_task_requires_repair(self):
        self.ledger_command("start", task="work-other-task")
        self.assert_repair(self.hook())

    def test_session_cannot_consume_another_sessions_path(self):
        self.ledger_command("start")
        other_session = "another-real-session"
        prompt = self.hook(session_id=other_session)
        self.assert_repair(prompt)
        # The asking session owns no interval of its own and never consumes the
        # other session's measured time.
        self.assertNotIn("source=interval-ledger", prompt)
        self.assertFalse(self.ledger_path(other_session).exists())

    def test_unknown_session_cannot_establish_ownership(self):
        self.session_id = "unknown-session"
        self.ledger = self.ledger_path(self.session_id)
        self.ledger_command("start")
        self.assert_repair(self.hook())

    def test_missing_ledger_demands_repair_and_labels_estimate(self):
        prompt = self.hook()
        self.assertIn("Active interval accounting is missing or unavailable", prompt)
        self.assertIn("begin measuring forward with lhc_active_time.py", prompt)
        self.assertIn("pause during idle waits", prompt)
        self.assertIn("Historical unknown time stays unknown", prompt)
        self.assertIn("active source=hook-observed", prompt)
        self.assertIn("estimated 0 active minutes", prompt)
        self.assertIn("hook-observed estimate only", prompt)
        self.assertNotIn("source=interval-ledger", prompt)
        self.assertNotIn("reported 0 active minutes", prompt)
        self.assertFalse(self.ledger.exists(), "Hook must not implicitly start measurement")


if __name__ == "__main__":
    unittest.main()
