"""The plan artifacts must be one procedure, not a discovery problem.

An AI session that had to produce the leaf files, the machine-readable graph and
the dashboard did not follow a written procedure: it read `lhc_grid.py` to find
the `check-plan` parser regexes, hunted the report regexes and the status
legend, and inferred the shape from an old task record. The package must carry
the procedure itself, so the agent copies it instead of reverse-engineering it.

The failure was a trigger failure as much as a content failure: no skill
description carried "plan", "graph", "dashboard" or "check-plan", so nothing in
the catalog was selected when a task was decomposed. The description is the part
an agent reads before loading anything, so it has to carry the trigger words.

The procedure is leaf-first. One leaf is one JSON file under `leaves/`, and the
owner of a leaf changes his own file and nothing else, so parallel workers
never collide. The collector gathers those files into `plan.graph.json`, the
renderer builds the page from that graph, and `check-plan` proves the readable
report and the graph are still one set of leaves. A plan without a `leaves/`
directory keeps the old report-first way of working; the skill says so instead
of pretending the old way is gone.

The model gate belongs here too: below 20% remaining allowance no council, no
frontier model and no adviser may be convened.
"""
import re
from pathlib import Path

from _inprocess import load_module, run_cli

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'src/common/skills'
PACKAGE = ROOT / 'plugins/last-human-commit'
CANON = SKILLS / 'plan-artifacts/SKILL.md'
UMBRELLA = SKILLS / 'last-human-commit/SKILL.md'
ROUTER = ROOT / 'AGENTS.md'
LEAD = ROOT / 'src/common/agents/Lead.md'
VALIDATOR = PACKAGE / 'scripts/validate.py'
TOOLS = ROOT / 'src/common/tools'
COLLECTOR = TOOLS / 'lhc_plan_json.py'
GRID = TOOLS / 'lhc_grid.py'
ENTRY = TOOLS / 'lhc_entry.py'
REPORT_PROTOCOL = ROOT / 'src/common/protocols/PLAN_REPORT.md'
GRAPH_PROTOCOL = ROOT / 'src/common/protocols/TASK_GRAPH.md'

# The three documents a person reads one after another. A field with two
# meanings, or a plan with two sources, is a defect the reader has to find.
PLAN_DOCUMENTS = (
    ('PLAN_REPORT.md', REPORT_PROTOCOL),
    ('TASK_GRAPH.md', GRAPH_PROTOCOL),
    ('plan-artifacts/SKILL.md', CANON),
)

# The meaning of `business_result`: the achieved fact, the person can use it
# already now.
ACHIEVED_MARKERS = (
    'уже сейчас',
    'достигнутый факт',
    'can already use',
    'achieved fact',
)

# The meaning the field must not carry: a benefit that only exists once the
# work is done. The two of them together are the defect.
FUTURE_MARKERS = (
    'после реализации',
    'after the task is complete',
    'after the work is complete',
)


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


def subcommands(tool: Path) -> set:
    """The real subcommands of a tool, as its own parser reports them."""

    out = run(tool, '--help')
    assert out.returncode == 0, f"{tool.name} --help failed: {out.stderr}"
    found = re.search(r"\{([\w,-]+)\}", out.stdout)
    assert found, f"{tool.name} --help names no subcommands"
    return set(found.group(1).split(','))


def run(*args):
    """Run a tool of the suite as its own CLI, without a new interpreter.

    The tool, its argument vector, its stdin, its stdout, its stderr and its
    exit code are the ones the command line would have produced; only the
    process boundary is saved.
    """

    tool = Path(args[0])
    result = run_cli(load_module(tool), [str(item) for item in args[1:]])
    return result


def write_plan(root: Path, leaves: dict, plan: dict = None) -> Path:
    """A plan directory of leaf files, as the skill describes them."""

    (root / 'leaves').mkdir(parents=True, exist_ok=True)
    for name, body in leaves.items():
        (root / 'leaves' / f'{name}.json').write_text(
            body if isinstance(body, str) else __import__('json').dumps(body),
            encoding='utf-8',
        )
    if plan is not None:
        (root / 'plan.json').write_text(
            __import__('json').dumps(plan, ensure_ascii=False), encoding='utf-8',
        )
    return root


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


def test_the_leaf_file_is_the_source_of_truth_of_a_leaf():
    body = flat(CANON.read_text())
    # The layout the Lead creates: one directory, one file per leaf.
    assert '<plan-dir>/leaves/L01.json' in body
    assert '<plan-dir>/plan.json' in body
    assert '<plan-dir>/plan.graph.json' in body
    # One file, one leaf, one owner — that is why parallel workers do not collide.
    assert 'one leaf — one file — one owner' in body
    assert 'the source of truth of its leaf' in body
    assert 'nobody writes them by hand' in body
    # The collector, not the agent, writes the graph.
    assert 'Do not hand-write the graph' in body
    assert '"<tools>/lhc_plan_json.py" build' in body
    assert '"<tools>/lhc_plan_json.py" check' in body
    # The page is a projection of the same graph revision.
    assert '"<tools>/lhc_grid.py" render' in body
    assert 'plan.html' in body and 'plan.md' in body


def test_the_skill_names_every_field_a_leaf_file_may_carry():
    """A field the collector accepts but the skill omits is a trap."""

    import importlib.util

    spec = importlib.util.spec_from_file_location('lhc_plan_json', COLLECTOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    body = flat(CANON.read_text())
    for field in module.LEAF_FIELDS:
        assert field in body, f"the skill never names the leaf field {field}"
    # The old attribution fields are not leaf fields: the collector rejects them.
    for field in ('role', 'read_paths', 'write_paths', 'paths'):
        assert f"`{field}`" in body
    assert 'are **not** leaf fields' in body


def meaning_windows(text: str, window: int = 240) -> list:
    """The text that follows every mention of the field label, flattened.

    A definition is the label and the meaning that comes with it, so the window
    is what a reader gets from the line that names the field.
    """

    body = flat(text)
    lowered = body.lower()
    out = []
    for label in ('business_result', 'бизнес-результат'):
        start = 0
        while True:
            at = lowered.find(label, start)
            if at < 0:
                break
            out.append(body[at:at + window])
            start = at + len(label)
    return out


def test_business_result_has_one_meaning_in_the_three_plan_documents():
    """One field, one meaning: the achieved fact, paired with the progress.

    The field used to be defined twice in the same report template — "what the
    person can already use now" and "the benefit the person gets after the
    work is done" — and a plan could therefore either pass a promised benefit
    off as a fact or write a technical status into the target field.
    """

    for name, path in PLAN_DOCUMENTS:
        windows = meaning_windows(path.read_text())
        assert windows, f"{name} never names business_result"
        for window in windows:
            for marker in FUTURE_MARKERS:
                assert marker.lower() not in window.lower(), (
                    f"{name} gives business_result a second meaning: {marker!r} "
                    f"sits next to the achieved fact in {window[:160]!r}"
                )
        assert any(
            any(marker in window.lower() for marker in ACHIEVED_MARKERS)
            for window in windows
        ), f"{name} never says that business_result is the achieved fact"
        # The pair is named explicitly, so the progress is not read as the result.
        assert 'current_progress' in flat(path.read_text()), (
            f"{name} never pairs business_result with current_progress"
        )


def test_the_source_of_the_plan_is_the_leaf_file_in_the_three_documents():
    """One source of the plan: the file of the leaf, not the graph."""

    old_claim = 'The graph is the canonical artifact'
    source_markers = {
        'PLAN_REPORT.md': 'The leaf file is the source of truth',
        'TASK_GRAPH.md': 'leaves/<ID>.json',
        'plan-artifacts/SKILL.md': 'The leaf file is the source of truth of its leaf',
    }
    for name, path in PLAN_DOCUMENTS:
        body = flat(path.read_text())
        assert old_claim not in body, (
            f"{name} still calls the graph the canonical artifact"
        )
        assert source_markers[name] in body, (
            f"{name} does not name the file of the leaf as the source of the plan"
        )


def test_the_hook_promise_names_the_harnesses_it_was_checked_in():
    """The page rebuilds itself only where the LHC write hook is registered."""

    for name, path in PLAN_DOCUMENTS:
        body = flat(path.read_text())
        if 'LHC write hook' not in body and 'lhc_entry.py' not in body:
            continue
        for harness in ('codex', 'claude-code', 'zcode', 'opencode', 'hermes'):
            assert harness in body, (
                f"{name} promises a self-rebuilding page without naming {harness}"
            )


def test_the_status_vocabulary_and_the_estimate_rule_are_in_the_skill():
    body = flat(CANON.read_text())
    for status in ('done', 'running', 'blocked', 'waiting', 'deferred', 'queued'):
        assert status in body
    assert 'estimate_unknown_reason' in body
    assert 'never rewritten to fit' in body
    assert "user's language" in body
    # The clock format and the two different numbers about time.
    assert 'ЧЧ:ММ' in body
    assert 'actual_minutes' in body and 'started_at' in body


def test_the_old_path_stays_available_for_a_plan_without_leaves():
    """The skill must not lie about the plans that have no leaf files."""

    body = flat(CANON.read_text())
    assert '"<tools>/lhc_grid.py" export' in body
    assert '--merge' in body
    assert 'carry it through every later refresh' in body
    # What the collector says when the plan is not a leaf-file plan.
    assert 'каталог leaves/ не найден' in body
    # The fields --merge carries, as opposed to the leaf fields.
    for field in ('role', 'read_paths', 'write_paths', 'paths'):
        assert f"`{field}`" in body


def test_the_auto_rebuild_and_the_live_page_are_described():
    body = flat(CANON.read_text())
    # The agent does not have to remember the commands.
    assert 'lhc_entry.py' in body
    assert 'rebuilds the graph' in body
    assert 'LHC: страница плана пересобрана' in body
    # The live page: the poller and the honest limit of a file:// page.
    assert 'every two seconds' in body
    assert 'file://' in body
    assert 'python3 -m http.server' in body


def test_the_reconcile_is_the_gate():
    body = flat(CANON.read_text())
    assert '"<tools>/lhc_grid.py" check-plan' in body
    assert 'exits non-zero' in body
    # The report shape, in the user's language.
    assert 'Цель:' in body
    assert 'Бизнес-результат:' in body
    assert 'Декомпозиция:' in body
    assert '## Plan' in body
    assert 'update the leaf file' in body


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
    # The umbrella names the new order, not the old report-first order.
    assert '(leaf files, graph, page, report, check)' in umbrella
    router = flat(ROUTER.read_text())
    assert 'The procedure is the `plan-artifacts` skill' in router
    assert 'leaves/<ID>.json' in router
    assert len(ROUTER.read_text().splitlines()) <= 200


def test_the_refresh_keeps_the_attribution_without_a_manual_edit():
    body = flat(CANON.read_text())
    assert '--merge' in body
    assert 'carry it through every later refresh' in body
    # The merge is a real verb of the tool, not a promise in prose.
    tool = GRID.read_text()
    assert '"--merge"' in tool
    assert 'def merge_attribution' in tool


def test_a_refresh_keeps_the_attribution_of_the_leaves(tmp_path):
    """The refresh must not force a manual edit of the graph JSON."""

    import json

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
    assert run(GRID, 'export', record, '-o', first).returncode == 0
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
    assert run(GRID, 'export', record, '-o', second, '--merge', first).returncode == 0
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


def test_the_documented_leaf_path_builds_the_graph_and_the_page(tmp_path):
    """The path the skill documents must work exactly as it is written."""

    import json

    plan = write_plan(
        tmp_path / 'plan',
        {
            'L01': {
                'id': 'L01', 'label': 'Первый лист', 'status': 'done',
                'description': 'Что делает первый лист.',
                'estimate_minutes': {'minimum': 10, 'maximum': 15},
                'actual_minutes': 7, 'started_at': '10:00', 'finished_at': '10:07',
            },
            'L02': {
                'id': 'L02', 'label': 'Второй лист', 'status': 'running',
                'depends_on': ['L01'],
                'estimate_minutes': {'minimum': 20, 'maximum': 30},
                # A leaf above the fifteen-minute cap passes only with the
                # reason it is deliberately larger — the rule the skill names.
                'estimate_over_limit_reason': 'Один длинный блок без точки разрыва.',
                'started_at': '10:10',
            },
        },
        {'title': 'План проверки', 'goal': 'Проверить', 'slots': 2},
    )

    checked = run(COLLECTOR, 'check', plan)
    assert checked.returncode == 0, checked.stderr

    built = run(COLLECTOR, 'build', plan)
    assert built.returncode == 0, built.stderr
    graph = plan / 'plan.graph.json'
    assert graph.is_file()

    document = json.loads(graph.read_text(encoding='utf-8'))
    assert document['schema_version'] == 2
    assert document['title'] == 'План проверки'
    assert [task['id'] for task in document['tasks']] == ['L01', 'L02']
    assert document['tasks'][1]['depends_on'] == ['L01']

    rendered = run(GRID, 'render', graph, '--out-dir', plan)
    assert rendered.returncode == 0, rendered.stderr
    assert (plan / 'plan.html').is_file()
    assert (plan / 'plan.md').is_file()

    # The collection is deterministic: the same leaves give the same graph.
    before = graph.read_bytes()
    assert run(COLLECTOR, 'build', plan).returncode == 0
    assert graph.read_bytes() == before


def test_the_collector_names_the_broken_leaf_file(tmp_path):
    """A broken leaf is named, never silently dropped."""

    plan = write_plan(tmp_path / 'plan', {'L12': '{"id": "L12", "label":'})
    result = run(COLLECTOR, 'build', plan)
    assert result.returncode != 0
    assert 'L12.json' in result.stderr
    assert 'битый JSON' in result.stderr


def test_a_plan_without_leaves_is_not_a_leaf_plan(tmp_path):
    """The old way of working stays available for a plan with no leaf files."""

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
    # The collector refuses such a plan and says why.
    refused = run(COLLECTOR, 'build', tmp_path)
    assert refused.returncode != 0
    assert 'leaves/' in refused.stderr
    # The old path still builds the same graph and the same page.
    graph = tmp_path / 'plan.graph.json'
    assert run(GRID, 'export', record, '-o', graph).returncode == 0
    assert run(GRID, 'render', graph, '--out-dir', tmp_path).returncode == 0
    assert (tmp_path / 'plan.html').is_file()
    # And the gate still compares the report with the graph.
    assert run(GRID, 'check-plan', record, graph).returncode == 0


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
    """The skill must not name a command that does not exist."""

    text = CANON.read_text()
    for tool in (GRID, COLLECTOR):
        real = subcommands(tool)
        for command in set(re.findall(rf'{tool.name}" ([\w-]+)', text)):
            assert command in real, f"{tool.name} has no command {command}"
    for command in ('export', 'render', 'check-plan', 'status', 'validate'):
        assert f'"{command}"' in GRID.read_text()
    for command in ('build', 'check'):
        assert f'"{command}"' in COLLECTOR.read_text()
    # The hook the skill names is a real file.
    assert ENTRY.is_file()


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
    availability = flat((SKILLS / 'model-availability/SKILL.md').read_text())
    # GLM reports usage, MiniMax reports what is left, Codex reports usage.
    assert 'GLM `percentage` is used, not remaining' in availability
    assert 'current_weekly_remaining_percent' in availability
    assert '`usedPercent` is used' in availability
    assert re.search(r'83% used is 17% remaining', availability)
