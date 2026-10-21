"""Independent engineering review must bind its assessment, not later bookkeeping."""
import json
from pathlib import Path

from test_outcome_contract import anchored, cli, review_export
from lhc_outcome_review import browser_journey, real_observation


URL = 'https://new.auto-gram.ru/chat/2122?cabinet=6'
AGENT_BROWSER = '/home/roomhacker/.npm-global/bin/agent-browser'


NATIVE_CWD = str(Path('/tmp').resolve())


def _browser_call(command, *, name='exec_command'):
    return {'name': name, 'arguments': json.dumps({'cmd': command}),
            '_native_cwd': NATIVE_CWD, '_exit_code': 0}


def _append_bookkeeping(manifest, text):
    data = json.loads(manifest.read_text())
    native_path = Path(data['target']['source']['location'])
    rows = [json.loads(line) for line in native_path.read_text().splitlines()]
    rows.append({'type': 'response_item', 'timestamp': rows[-1]['timestamp'], 'payload': {
        'type': 'message', 'role': 'assistant', 'phase': 'final', 'content': [{'text': text}]}})
    raw = ''.join(json.dumps(row) + '\n' for row in rows)
    native_path.write_text(raw)
    Path(data['target']['path']).write_text(raw)


def _move_consumer_after_assessment(manifest):
    data = json.loads(manifest.read_text())
    native_path = Path(data['target']['source']['location'])
    rows = [json.loads(line) for line in native_path.read_text().splitlines()]
    report_index = next(i for i, row in enumerate(rows)
                        if 'LHC_OUTCOME_REVIEW ' in json.dumps(row.get('payload', {}).get('content', [])))
    pair_indexes = [i for i, row in enumerate(rows)
                    if row.get('payload', {}).get('call_id') == 'call-1']
    pair = [rows[i] for i in pair_indexes]
    for i in reversed(pair_indexes):
        rows.pop(i)
    report_index = next(i for i, row in enumerate(rows)
                        if 'LHC_OUTCOME_REVIEW ' in json.dumps(row.get('payload', {}).get('content', [])))
    rows[report_index + 1:report_index + 1] = pair
    raw = ''.join(json.dumps(row) + '\n' for row in rows)
    native_path.write_text(raw)
    Path(data['target']['path']).write_text(raw)


def test_independent_engineering_uses_original_assessment_before_later_bookkeeping(tmp_path):
    outcome = anchored(tmp_path)
    manifest = review_export(tmp_path, outcome)
    _append_bookkeeping(manifest, 'Already delivered the requested line; administrative handoff is complete.')

    result = cli(tmp_path, 'review', '--manifest', str(manifest))

    assert result['finish_verdict'] == 'complete'
    assert result['canary']['status'] == 'complete'


def test_later_negative_independent_assessment_is_not_skipped(tmp_path):
    outcome = anchored(tmp_path)
    manifest = review_export(tmp_path, outcome)
    _append_bookkeeping(manifest, 'Changes required: the consumer output does not match the expected result.')

    error = cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)

    assert 'product result does not satisfy engineering canary' in error
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_consumer_call_after_assessment_cannot_repair_missing_pre_report_witness(tmp_path):
    outcome = anchored(tmp_path)
    manifest = review_export(tmp_path, outcome)
    _move_consumer_after_assessment(manifest)
    _append_bookkeeping(manifest, 'Already delivered the requested line.')

    error = cli(tmp_path, 'review', '--manifest', str(manifest), ok=False)

    assert 'actual native calls' in error or 'subsequent real CLI readback' in error
    assert cli(tmp_path, 'status')['finish_verdict'] == 'pending'


def test_documented_env_prefix_binds_exact_browser_target_and_native_journey():
    prefix = f'env -u AGENT_BROWSER_AUTO_CONNECT {AGENT_BROWSER}'
    opened = _browser_call(f'{prefix} --session lhc-proof open {URL}')
    clicked = _browser_call(f'{prefix} --session lhc-proof click @return-link')
    snapshot = _browser_call(f'{prefix} --session lhc-proof snapshot -i')
    assert real_observation(opened, 'Opened page ' + URL, URL, 'consumer', 'fullcycle', cwd=Path(NATIVE_CWD))
    pathless = _browser_call(f'env -u AGENT_BROWSER_AUTO_CONNECT agent-browser --session lhc-proof open {URL}')
    assert real_observation(pathless, 'Opened page ' + URL, URL, 'consumer', 'fullcycle', cwd=Path(NATIVE_CWD))
    assert not real_observation(opened, 'Opened page ' + URL, 'https://other.example/chat', 'consumer', 'fullcycle', cwd=Path(NATIVE_CWD))
    journey = {'open': (opened, 'Opened page ' + URL),
               'click': (clicked, 'Clicked return link'),
               'snapshot': (snapshot, 'Returned to dialogs page')}
    assert browser_journey(list(journey), journey, URL)


def test_env_normalization_rejects_other_mutations_and_non_browser():
    browser = f'{AGENT_BROWSER} --session lhc-proof open {URL}'
    wrong_env = _browser_call(f'env -u PATH {browser}')
    assert not real_observation(wrong_env, 'Opened page ' + URL, URL, 'consumer', 'fullcycle', cwd=Path(NATIVE_CWD))
    mislabeled_browser = _browser_call(f'env -u PATH {browser}', name='browser.open')
    assert not real_observation(mislabeled_browser, 'Opened page ' + URL, URL, 'consumer', 'fullcycle', cwd=Path(NATIVE_CWD))
    echo = _browser_call(f'env -u AGENT_BROWSER_AUTO_CONNECT /bin/echo {URL}')
    assert not real_observation(echo, URL, URL, 'consumer', 'fullcycle', cwd=Path(NATIVE_CWD))
    compound = _browser_call(f'env -u AGENT_BROWSER_AUTO_CONNECT {browser} && /bin/echo done')
    assert not real_observation(compound, 'Opened page ' + URL, URL, 'consumer', 'fullcycle', cwd=Path(NATIVE_CWD))
