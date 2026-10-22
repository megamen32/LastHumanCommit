"""The plan artifacts must be one procedure, not a discovery problem.

An AI session that had to produce the task record, the machine-readable graph and
the dashboard did not follow a written procedure: it read `lhc_grid.py` to find
the `check-plan` parser regexes, hunted the report regexes and the status legend,
and inferred the shape from an old task record. The package must carry the
procedure itself, so the agent copies it instead of reverse-engineering it.

The failure was a trigger failure as much as a content failure: no skill
description carried "plan", "graph", "dashboard" or "check-plan", so nothing in
the catalog was selected when a task was decomposed. The description is the part
an agent reads before loading anything, so it has to carry the trigger words.

The procedure is report-first. The report is the only format a person reads, and
the tool derives the graph from it — the agent writes one format, not two, and
never hand-writes the graph JSON. What the report cannot carry (owner, session,
paths, note) is added to the exported graph afterwards, and `check-plan` is the
gate that proves report and graph are one set of leaves.

The same session showed that the tool path convention was broken: a skill
pointed at `../../tools/lhc_grid.py`, which resolves in the package projections
but not in the repository-root projection of the skills tree.

The model gate belongs here too: below 20% remaining allowance no council, no
frontier model and no adviser may be convened.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'src/common/skills'
PACKAGE = ROOT / 'plugins/last-human-commit'
CANON = SKILLS / 'plan-artifacts/SKILL.md'
UMBRELLA = SKILLS / 'last-human-commit/SKILL.md'
ROUTER = ROOT / 'AGENTS.md'
LEAD = ROOT / 'src/common/agents/Lead.md'
VALIDATOR = PACKAGE / 'scripts/validate.py'


def flat(text: str) -> str:
    return " ".join(text.split())


def front_matter(text: str) -> dict:
    assert text.startswith('---\n')
    block = text.split('---\n', 2)[1]
    out = {}
    for line in block.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            out[key.strip()] = value.strip()
    return out


def test_the_procedure_lives_in_its_own_skill():
    assert CANON.is_file()
    meta = front_matter(CANON.read_text())
    assert meta['name'] == 'plan-artifacts'
    # The description is the only thing an agent reads before loading anything,
    # so it has to trigger on the words the work actually uses.
    description = meta['description'].lower()
    for trigger in ('decompose', 'plan', 'dashboard', 'graph', 'check-plan'):
        assert trigger in description
    assert 'never reverse-engineer' in description


def test_the_skill_is_report_first_and_never_asks_for_hand_written_json():
    body = flat(CANON.read_text())
    # One format for a person; the graph is derived from it.
    assert 'Do not hand-write the graph' in body
    assert '"<tools>/lhc_grid.py" export' in body
    assert '"<tools>/lhc_grid.py" check-plan' in body
    assert '"<tools>/lhc_grid.py" render' in body
    # The report shape, in the user's language.
    assert 'Цель:' in body
    assert 'Бизнес-результат:' in body
    assert 'Декомпозиция:' in body
    assert '## Plan' in body
    # The gate and the boundary order.
    assert 'exits non-zero' in body
    assert 'update the report in the record' in body
    # Only the fields the export cannot carry are named as such: the export
    # already copies owner, session, harness, model, note and the rest.
    assert 'Set the attribution once' in body
    for field in ('role', 'read_paths', 'write_paths', 'current_progress', 'external_waits'):
        assert f'`{field}`' in body
    # The status vocabulary and the estimate rule.
    for status in ('done', 'running', 'blocked', 'waiting', 'queued'):
        assert status in body
    assert 'estimate_unknown_reason' in body
    assert "user's language" in body


def test_no_skill_points_at_a_tool_path_that_breaks_in_a_shipped_layout():
    # `../../tools/...` resolves in the package projections and breaks in the
    # repository-root projection of the skills tree.
    for skill in SKILLS.glob('*/SKILL.md'):
        text = skill.read_text()
        assert '../../tools/' not in text, f"{skill.name} uses a broken tool path"
        assert 'python3 "src/common/tools/' not in text, f"{skill.name} uses a package-only path"
    readme = flat((SKILLS / 'README.md').read_text())
    assert '"<tools>/..."' in readme


def test_the_umbrella_skill_and_the_router_point_to_the_procedure():
    umbrella = flat(UMBRELLA.read_text())
    assert 'plan-artifacts' in umbrella
    assert 'it is the procedure' in umbrella
    router = flat(ROUTER.read_text())
    assert 'The procedure is the `plan-artifacts` skill' in router
    assert 'the graph is derived from it with `lhc_grid.py export`' in router
    assert len(ROUTER.read_text().splitlines()) <= 200


def test_the_refresh_keeps_the_attribution_without_a_manual_edit():
    body = flat(CANON.read_text())
    assert '--merge' in body
    assert 'the attribution survives' in body
    # The merge is a real verb of the tool, not a promise in prose.
    import re
    tool = (ROOT / 'src/common/tools/lhc_grid.py').read_text()
    assert '"--merge"' in tool
    assert 'def merge_attribution' in tool


def test_a_refresh_keeps_the_attribution_of_the_leaves(tmp_path):
    """The refresh must not force a manual edit of the graph JSON."""

    import json
    import subprocess

    tool = ROOT / 'src/common/tools/lhc_grid.py'
    record = tmp_path / 'task.md'
    record.write_text(
        "# Task\n\n## Plan\n"
        "Цель: собрать артефакты\n"
        "Бизнес-результат: отчёт, граф и дашборд\n"
        "Декомпозиция: 2 листа · параллельно нет · 1 волна · слотов: 1\n\n"
        "✅ (первый лист) начата 10:00 закончена 10:05, оценка 10 минут, факт 5 минут\n"
        "🔄 работаем (второй лист) начата 10:06, оценка 10 минут, прошло 4 минуты\n",
        encoding='utf-8',
    )
    first = tmp_path / 'plan.graph.json'
    subprocess.run(
        [sys.executable, str(tool), 'export', str(record), '-o', str(first)],
        check=True, capture_output=True,
    )
    document = json.loads(first.read_text(encoding='utf-8'))
    document['title'] = 'Мой заголовок'
    document['current_progress'] = 'первый лист закрыт'
    document['tasks'][0].update({
        'role': 'Worker',
        'write_paths': ['src/b.ts'],
        'owner': 'mvs_x',
        'session': 'codex:1',
    })
    first.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')

    second = tmp_path / 'plan2.graph.json'
    subprocess.run(
        [sys.executable, str(tool), 'export', str(record), '-o', str(second),
         '--merge', str(first)],
        check=True, capture_output=True,
    )
    refreshed = json.loads(second.read_text(encoding='utf-8'))
    leaf = refreshed['tasks'][0]
    assert leaf['role'] == 'Worker'
    assert leaf['write_paths'] == ['src/b.ts']
    assert leaf['owner'] == 'mvs_x'
    assert leaf['session'] == 'codex:1'
    assert refreshed['current_progress'] == 'первый лист закрыт'
    assert refreshed['title'] == 'Мой заголовок'
    # The report still drives the state of the work.
    assert leaf['status'] == 'done'


def test_the_skill_is_registered_in_the_validator_and_the_catalog():
    validator = VALIDATOR.read_text()
    assert '"plan-artifacts",' in validator
    catalog = (SKILLS / 'README.md').read_text()
    assert '[plan-artifacts](plan-artifacts/SKILL.md)' in catalog


def test_the_shipped_package_carries_the_same_procedure():
    projected = PACKAGE / 'skills/plan-artifacts/SKILL.md'
    assert projected.is_file()
    assert projected.read_text() == CANON.read_text()
    for root in (PACKAGE, PACKAGE / 'native/codex'):
        assert (root / 'skills/plan-artifacts/SKILL.md').is_file()


def test_the_reported_commands_are_real_commands_of_the_tool():
    # The skill must not name a command that does not exist.
    import re
    tool = (ROOT / 'src/common/tools/lhc_grid.py').read_text()
    for command in set(re.findall(r'lhc_grid\.py" (\w[\w-]*)', CANON.read_text())):
        assert f'"{command}"' in tool, f"lhc_grid.py has no command {command}"
    for command in ('export', 'render', 'check-plan', 'status', 'validate'):
        assert f'"{command}"' in tool


def test_below_twenty_percent_no_council_no_frontier_model_no_adviser():
    availability = flat((SKILLS / 'model-availability/SKILL.md').read_text())
    assert 'The 20% allowance gate' in availability
    assert 'below 20%' in availability
    assert 'no council, no frontier model, no adviser' in availability
    assert "The owner's explicit instruction in the moment overrides the gate" in availability
    council = flat((SKILLS / 'council/SKILL.md').read_text())
    assert 'below 20%' in council
    assert 'does not sit in a council' in council
    assert 'less than 20%' in flat(ROUTER.read_text())
    assert 'less than 20%' in flat(LEAD.read_text())


def test_the_gate_reads_the_units_before_it_applies():
    import re
    availability = flat((SKILLS / 'model-availability/SKILL.md').read_text())
    # GLM reports usage, MiniMax reports what is left, Codex reports usage.
    assert 'GLM `percentage` is used, not remaining' in availability
    assert 'current_weekly_remaining_percent' in availability
    assert '`usedPercent` is used' in availability
    assert re.search(r'83% used is 17% remaining', availability)
