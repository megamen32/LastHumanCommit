"""CI gate for the one version counter (runs in the existing site test step)."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "common" / "tools"))
import lhc_version  # noqa: E402


class VersionCounter(unittest.TestCase):
    def test_repeated_versions_agree_with_the_version_file(self):
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_version.py"), "--check"],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout)

    @unittest.skipUnless(os.environ.get("GITHUB_EVENT_NAME") == "pull_request",
                         "only a change that is about to land must raise the version")
    def test_a_pull_request_raises_the_version_by_exactly_one_step(self):
        fetched = subprocess.run(["git", "-C", str(ROOT), "fetch", "--quiet", "--depth=1", "origin", "main"],
                                 capture_output=True, text=True)
        if fetched.returncode:
            self.skipTest("main cannot be fetched here")
        shown = subprocess.run(["git", "-C", str(ROOT), "show", "FETCH_HEAD:VERSION"], capture_output=True, text=True)
        if shown.returncode:
            self.skipTest("main has no VERSION file yet")
        result = lhc_version.check(ROOT, "FETCH_HEAD")
        self.assertTrue(result["ok"], result.get("reason"))


if __name__ == "__main__":
    unittest.main()
