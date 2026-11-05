"""The plan mirror release tool: hash, build, canary, switch, rollback (no real systemd)."""
import hashlib
import json
from pathlib import Path
import socket
import sys

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'src/common/tools'
sys.path.insert(0, str(TOOLS))
import lhc_plan_mirror_release as release  # noqa: E402


def make_source(tmp_path, marker='a'):
    source = tmp_path / ('source-' + marker)
    source.mkdir(exist_ok=True)
    (source / 'lhc_plan_mirror.py').write_text('# mirror ' + marker + '\n')
    (source / 'lhc_other.py').write_text('X = 1\n')
    (source / 'notes.txt').write_text('ignored')
    (source / "__pycache__").mkdir(exist_ok=True)
    (source / '__pycache__/lhc_other.cpython-312.pyc').write_bytes(b'ignored')
    return source


class Systemd:
    def __init__(self, fail=None):
        self.calls, self.fail = [], fail

    def __call__(self, argv, *, timeout=60):
        self.calls.append(argv[2:] if argv[:2] == ['systemctl', '--user'] else argv)
        if self.fail and self.fail in argv and self.fail_left:
            self.fail_left -= 1
            return 1, 'failed'
        return 0, 'active'

    fail_left = 1


@pytest.fixture
def host(tmp_path, monkeypatch):
    base, config, units = tmp_path / 'base', tmp_path / 'config', tmp_path / 'units'
    config.mkdir()
    (config / 'client.json').write_text('{"c": 1}')
    (config / 'server.json').write_text('{"s": 1}')
    (config / 'write-token').write_text('secret-secret-secret-secret-secret')
    (base / 'client').mkdir(parents=True)
    (base / 'client/registry.json').write_text('{"plans": {}}')
    systemd = Systemd()
    monkeypatch.setattr(release, 'run_command', systemd)
    common = ['--base', str(base), '--config-dir', str(config), '--units-dir', str(units), '--python', sys.executable]
    return base, config, units, systemd, common


def call(common, *words, capsys=None):
    code = release.main([*common, *words])
    out = capsys.readouterr().out if capsys else ''
    return code, (json.loads(out) if out.strip() else None)


def test_hash_is_sha256_of_names_and_bytes_of_py_files_only(tmp_path):
    source = make_source(tmp_path)
    expected = hashlib.sha256()
    for name in ('lhc_other.py', 'lhc_plan_mirror.py'):
        expected.update(name.encode())
        expected.update((source / name).read_bytes())
    assert release.tools_hash(source) == expected.hexdigest()[:16]
    (source / 'notes.txt').write_text('changed')
    (source / '__pycache__/x.pyc').write_bytes(b'new')
    assert release.tools_hash(source) == expected.hexdigest()[:16]
    (source / 'lhc_other.py').write_text('X = 2\n')
    assert release.tools_hash(source) != expected.hexdigest()[:16]
    assert release.tools_hash(make_source(tmp_path, 'b')) != release.tools_hash(source)


def test_build_copies_the_release_without_switching(host, tmp_path, capsys):
    base, config, units, systemd, common = host
    source = make_source(tmp_path)
    code, result = call(common, 'build', '--source', str(source), capsys=capsys)
    assert code == 0 and result['built'] is True
    target = base / 'releases' / result['release']
    assert sorted(p.name for p in (target / 'tools').iterdir()) == ['lhc_other.py', 'lhc_plan_mirror.py']
    assert not (base / 'current').exists() and not units.exists() and systemd.calls == []
    code, again = call(common, 'build', '--source', str(source), capsys=capsys)
    assert again['built'] is False
    (target / 'tools/lhc_other.py').write_text('tampered')
    assert call(common, 'build', '--source', str(source))[0] == 1


def test_switch_backs_up_rewrites_units_and_restarts_in_order(host, tmp_path, capsys):
    base, config, units, systemd, common = host
    first = call(common, 'build', '--source', str(make_source(tmp_path, 'a')), capsys=capsys)[1]['release']
    second = call(common, 'build', '--source', str(make_source(tmp_path, 'b')), capsys=capsys)[1]['release']
    assert call(common, 'switch', first, capsys=capsys)[0] == 0
    systemd.calls.clear()
    code, result = call(common, 'switch', second, capsys=capsys)
    assert code == 0 and result['from'] == first
    assert systemd.calls[:4] == [['daemon-reload'], ['stop', 'lhc-plan-observer.service'],
                                 ['restart', 'lhc-plan-mirror.service'], ['start', 'lhc-plan-observer.service']]
    mirror = (units / 'lhc-plan-mirror.service').read_text()
    observer = (units / 'lhc-plan-observer.service').read_text()
    assert f'/releases/{second}/tools/lhc_plan_mirror.py" "serve" "--config"' in mirror
    assert f'/releases/{second}/tools/lhc_plan_mirror.py" "watch"' in observer
    assert (base / 'current').resolve() == (base / 'releases' / second).resolve()
    saved = Path(result['backup'])
    assert saved.name.startswith('backup-')
    assert (saved / 'config/client.json').is_file() and (saved / 'registry.json').is_file()
    assert not (saved / 'config/write-token').exists()
    assert f'/releases/{first}/' in (saved / 'units/lhc-plan-mirror.service').read_text()
    assert not (base / 'client/ingest.lock').exists()


def test_rollback_returns_to_the_previous_release(host, tmp_path, capsys):
    base, config, units, systemd, common = host
    ids = [call(common, 'build', '--source', str(make_source(tmp_path, m)), capsys=capsys)[1]['release'] for m in 'abc']
    for item in ids:
        assert call(common, 'switch', item, capsys=capsys)[0] == 0
    systemd.calls.clear()
    code, result = call(common, 'rollback', capsys=capsys)
    assert code == 0 and result['release'] == ids[1]
    assert unit_of(units) == ids[1] and systemd.calls[1] == ['stop', 'lhc-plan-observer.service']
    assert call(common, 'rollback', capsys=capsys)[1]['release'] == ids[0]
    assert unit_of(units) == ids[0]
    code, status = call(common, 'status', '--source', str(make_source(tmp_path, 'c')), capsys=capsys)
    assert status['current'] == ids[0] and status['previous'] == [] and status['units']['mirror']['release'] == ids[0]
    assert call(common, 'rollback')[0] == 1          # nothing before the first release
    assert call(common, 'rollback', '--to', ids[2], capsys=capsys)[1]['release'] == ids[2]


def unit_of(units):
    return release.unit_release(units / 'lhc-plan-mirror.service')


def test_a_failed_restart_puts_the_previous_release_back(host, tmp_path, capsys):
    base, config, units, systemd, common = host
    first = call(common, 'build', '--source', str(make_source(tmp_path, 'a')), capsys=capsys)[1]['release']
    second = call(common, 'build', '--source', str(make_source(tmp_path, 'b')), capsys=capsys)[1]['release']
    assert call(common, 'switch', first, capsys=capsys)[0] == 0
    systemd.fail = 'restart'
    assert call(common, 'switch', second)[0] == 1
    assert unit_of(units) == first and (base / 'current').resolve().name == first
    assert json.loads((base / 'release-state.json').read_text())['current'] == first


def test_names_and_paths_come_from_arguments_or_release_json(host, tmp_path, capsys):
    base, config, units, systemd, common = host
    (config / 'release.json').write_text(json.dumps({'mirror_unit': 'x-serve.service', 'observer_unit': 'x-watch.service'}))
    item = call(common, 'build', '--source', str(make_source(tmp_path)), capsys=capsys)[1]['release']
    assert call(common, 'switch', item, capsys=capsys)[0] == 0
    assert (units / 'x-serve.service').is_file() and ['restart', 'x-serve.service'] in systemd.calls
    assert call([*common, '--mirror-unit', 'y.service'], 'switch', item, capsys=capsys)[0] == 0
    assert (units / 'y.service').is_file()


def test_canary_runs_the_real_release_on_a_spare_port(host, tmp_path, capsys):
    base, config, units, systemd, common = host
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    item = call(common, 'build', '--source', str(TOOLS), capsys=capsys)[1]['release']
    code, result = call([*common, '--canary-port', str(port)], 'canary', item, capsys=capsys)
    assert code == 0 and result['html'] is True and result['steps'] == {'register': 'ok', 'once': 'ok'}
    assert not (base / 'current').exists() and systemd.calls == []
    with socket.socket() as busy:
        busy.bind(('127.0.0.1', 0))
        busy.listen()
        assert call([*common, '--canary-port', str(busy.getsockname()[1])], 'canary', item)[0] == 1
