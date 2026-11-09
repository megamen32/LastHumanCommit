import os
import subprocess
import pytest


def pytest_sessionstart(session):
    base = session.config._tmp_path_factory.getbasetemp()
    subprocess.run(['git', 'init', '--quiet', str(base)],check=True)
    (base / '.agents').mkdir(exist_ok=True)

@pytest.fixture(autouse=True)
def review_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'config'))
    monkeypatch.setenv('XDG_STATE_HOME', str(tmp_path / 'state'))
    monkeypatch.setenv('LHC_PLAN_MIRROR_CONFIG', str(tmp_path / 'no-mirror'))
    for key in ('CODEX_THREAD_ID','CLAUDE_SESSION_ID','OPENCODE_SESSION_ID','LHC_MCP_ACTOR_CONTEXT','AGENT_HERDER_HTTP_URL','AGENT_HERDER_HTTP_TOKEN'):
        monkeypatch.delenv(key,raising=False)
