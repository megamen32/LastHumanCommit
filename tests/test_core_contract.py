"""The core LHC contract, one test per defect observed in real sessions.

Each test names the failure it guards against. Wording may change; the rule may not.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import importlib.util
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def flat(relative: str) -> str:
    return " ".join((ROOT / relative).read_text(encoding="utf-8").split())


ROUTER = "AGENTS.md"


def test_a_turn_does_not_end_with_work_the_lead_could_do_itself():
    # 2026-10-26: sessions closed turns with "test data not created", "not checked
    # live: needs a login" and "next: deploy" while the owner was away.
    router = flat(ROUTER)
    assert "## Finish line" in (ROOT / ROUTER).read_text()
    assert "is a failed turn" in router
    for chore in ("Test users, test data, fixtures", "QA memberships", "expired test credentials"):
        assert chore in router, chore


def test_a_decline_is_parked_not_routed_around():
    router = flat(ROUTER)
    assert "A decline is a decision" in router
    assert "do not route around it" in router


def test_escalation_goes_lead_then_adviser_then_overseer_then_owner():
    # The Lead used to jump from a stuck Worker straight to the Overseer.
    text = (ROOT / ROUTER).read_text()
    chain = text[text.index("## When stuck"):text.index("## The cycle")]
    order = [chain.index(f"**{role}**") for role in ("Worker", "L", "Adviser", "Overseer", "Owner")]
    assert order == sorted(order)
    lead = flat("src/common/agents/Lead.md")
    assert lead.index("Then Adviser") < lead.index("then Overseer")
    assert "Step 4 of the escalation chain" in flat("src/common/agents/Overseer.md")
    assert "step 3 of the escalation chain" in flat("src/common/agents/Adviser.md")


def test_workers_return_blockers_instead_of_hunting_routes():
    # A cheap Worker searching for routes costs more than the Lead's context.
    worker = flat("src/common/agents/Worker.md")
    assert "One cheap attempt" in worker
    assert "I do not hunt for routes" in worker


def test_owner_repository_merges_to_main_and_foreign_repository_to_the_owner_branch():
    router = flat(ROUTER)
    assert "draft PR into `main`" in router
    assert "Green checks are evidence, not merge authorization" in router
    assert "Never push, merge or open a PR into the external owner's `main`" in router
    template = (ROOT / "src/common/templates/project.md").read_text()
    for field in ("owner:", "target:", "dev:"):
        assert re.search(rf"^{field}", template, re.MULTILINE), field
    package = ROOT / "plugins/last-human-commit/common/templates/project.md"
    assert package.read_bytes() == (ROOT / "src/common/templates/project.md").read_bytes()


def test_branch_publication_is_independent_but_last_worker_integrates():
    # Sessions in separate worktrees waited for a self-elected "release owner"
    # who forgot it was the owner.
    sources = " ".join(flat(path) for path in (
        ROUTER, "src/common/protocols/SHARED_WORKTREE.md",
        "src/common/protocols/OUTCOME_CONTRACT.md", "PRODUCT-PHILOSOPHY.md"))
    assert "last active worker owns" in sources
    assert "confirmed-inactive" in sources
    assert "Never blindly merge unknown branches" in sources
    assert "an early draft PR is recommended" in sources
    assert "LHC plan link" in sources
    assert "nobody waits" in sources
    for retired in ("one published dev history is mandatory", "unified published dev history",
                    "Airlock converges on megamen32-dev; Oleg owns upstream main"):
        assert retired not in sources, retired


def test_fullcycle_needs_two_testers_and_quickfix_one():
    router = flat(ROUTER)
    assert "at least two in a fullcycle" in router
    assert "Quickfix still requires a proportional independent tester" in router
    for path in ("src/common/protocols/OUTCOME_CONTRACT.md", "src/common/templates/project-router.md",
                 "src/common/skills/last-human-commit/SKILL.md"):
        assert "two independent testers of the installed consumer result" not in flat(path), path


def test_focus_group_does_what_the_owner_kept_asking_for():
    # Repeated owner requests, 2026-09-04 .. 2026-10-26.
    skill = flat("src/common/skills/focus-groups/SKILL.md")
    for rule in ("register new accounts", "part on mobile, part on desktop",
                 "what do you think this does?", "light and dark",
                 "Nobody waits for the owner", "except destructive actions",
                 "fresh personas"):
        assert rule in skill, rule


def test_quorum_triggers_the_council_and_stays_bounded():
    council = flat("src/common/skills/council/SKILL.md")
    assert "кворум" in council and "созови кворум" in council
    assert "about an hour, not days" in council
    assert "not in a question to the owner" in council


def test_background_protocols_yield_to_the_router():
    for name in ("OUTCOME_CONTRACT", "PLAN_REPORT", "TIME_CONTROL", "TASK_GRAPH",
                 "BUSINESS_CHECKPOINT", "ORCHESTRATION_RECORDS", "SELF_IMPROVE", "MEMORY"):
        head = (ROOT / f"src/common/protocols/{name}.md").read_text().splitlines()[0]
        assert head.startswith("> Background reference.") and "`AGENTS.md` wins" in head, name


def _guard():
    spec = importlib.util.spec_from_file_location("lhc_time_guard_core", ROOT / "src/common/tools/lhc_time_guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_time_reminders_never_tell_the_agent_to_stop(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    guard = _guard()
    start = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)
    guard.native_heartbeat(tmp_path, "codex", "core", now=start)
    due = guard.native_heartbeat(tmp_path, "codex", "core", now=start + timedelta(minutes=60))
    prompt = due["prompt"]
    assert "30-minute plan report" in prompt and "60-minute direction check" in prompt
    assert "keep working" in prompt
    assert "never ends the turn" in prompt and "never a reason to stop" in prompt


def test_parallel_release_requires_published_task_pr_and_fenced_lease():
    router = flat(ROUTER)
    assert "Do not implement in shared `main`" in router
    assert "lhc_worktree.py delivery" in router
    assert "project_release_lease" in router
    assert "expected-revision compare and swap" in router
    assert "not every ordinary turn end" in router
    protocol = flat("src/common/protocols/SHARED_WORKTREE.md")
    for required in ("SendMessage", "TTL", "finally", "foreign lease", "stale fence"):
        assert required in protocol
    assert "Mergeable and green: merge" not in protocol


def test_ownerless_work_is_adopted_after_bounded_lookup_not_blindly_merged():
    router = flat(ROUTER)
    protocol = flat("src/common/protocols/SHARED_WORKTREE.md")
    assert "bounded lookup finds no active owner" in router
    assert "record it in the current plan" in router
    assert "current worker must adopt responsibility" in protocol
    assert "not automatic acceptance or merge/deploy authorization" in protocol
    assert "recheck ownership before mutation" in protocol
    assert "never from owner absence alone" in protocol
