"""The native installer must extend, not replace, existing protected config."""
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'deploy/plan-mirror/install-native.py'
SPEC = importlib.util.spec_from_file_location('plan_mirror_installer', SCRIPT)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def test_config_merge_preserves_current_fields_and_only_adds_missing_defaults(tmp_path):
    path = tmp_path / 'client.json'
    path.write_text(
        '{"endpoint":"https://existing.example","roots":["/old/root"],'
        '"graph_sources":["/old/task/plan.graph.json"],"extra":{"keep":true}}'
    )

    config = installer.merge_config(path, {
        'endpoint': 'https://lhc.bezrabotnyi.com', 'mode': 'mirror',
        'sso_enabled': True,
    })
    config['roots'] = installer.merge_paths(config.get('roots', []), ['/new/root'], 'roots')
    config['graph_sources'] = installer.merge_paths(
        config.get('graph_sources', []), ['/new/task/plan.graph.json'], 'graph_sources')

    assert config['endpoint'] == 'https://existing.example'
    assert config['mode'] == 'mirror' and config['sso_enabled'] is True
    assert config['roots'] == ['/old/root', '/new/root']
    assert config['graph_sources'] == [
        '/old/task/plan.graph.json', '/new/task/plan.graph.json']
    assert config['extra'] == {'keep': True}
    assert installer.merge_paths(config['roots'], ['/old/root'], 'roots') == config['roots']


def test_root_sso_flag_changes_only_the_explicit_server_field(tmp_path):
    path = tmp_path / 'server.json'
    path.write_text(
        '{"listen":"127.0.0.1","port":8999,"token_file":"/protected/token",'
        '"dashboard_key_file":"/protected/key","sso_enabled":false,"custom":"keep"}'
    )
    config = installer.merge_config(path, {
        'listen': '127.0.0.1', 'port': 8769, 'sso_enabled': False,
        'data_dir': '/new/server-data',
    })
    config['sso_enabled'] = True

    assert config == {
        'listen': '127.0.0.1', 'port': 8999, 'token_file': '/protected/token',
        'dashboard_key_file': '/protected/key', 'sso_enabled': True,
        'custom': 'keep', 'data_dir': '/new/server-data',
    }
