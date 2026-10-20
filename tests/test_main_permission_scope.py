"""A main permission quote stays bound to its own native source and project scope."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_outcome as outcome  # noqa: E402
import lhc_time_guard as guard  # noqa: E402
from test_project_mapping import OWNED, REPOSITORY, setup_mapping  # noqa: E402


PERMISSION = (
    "Тебе разрешены сделать полностью все действия, включая деплой, "
    "мерж в main для секретаря, для всех проектов, кроме Airlock"
)
SID = "parent-session"
PROJECT_PROMPT = (
    "Исправь Last Human Commit в {root}; работай только с "
    "src/common/tools/lhc_outcome.py и tests/test_outcome_contract.py."
)


@pytest.fixture
def isolated_tmp_path():
    with tempfile.TemporaryDirectory(prefix="lhc-permission-test-") as directory:
        yield Path(directory)


def _source(prompt, turn):
    short = hashlib.sha256(prompt.strip().encode()).hexdigest()[:12]
    return {"source": f"native-user-prompt:{SID}:{turn}:{short}", "origin": "unknown",
            "prompt": prompt.strip()[:2048], "scope_prompt": outcome.semantic_scope(prompt)}


def _write_native(path, cwd, prompts):
    rows = [{"type": "session_meta", "payload": {"id": SID, "cwd": str(cwd)}}]
    for turn, prompt in prompts:
        rows.append({"type": "response_item", "timestamp": f"2026-10-21T10:0{len(rows)}:00Z",
                     "payload": {"type": "message", "role": "user", "content": [{"text": prompt}],
                                 "internal_chat_message_metadata_passthrough": {"turn_id": turn}}})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def setup_contract(tmp_path, monkeypatch, *, quote=PERMISSION, permission_prefix="Исходное поручение. ",
                   later=(), permission_origin="unknown", duplicate=False, hold=None,
                   remote_url="https://github.com/megamen32/LastHumanCommit.git",
                   same_message_suffix=""):
    tmp_path.mkdir(parents=True, exist_ok=True)
    project_prompt = "Так продолжай и доведи Last Human Commit до рабочего результата. Исправь оставшуюся проблему с публикацией исходников, проверь через Luna и Sol и установи."
    workspace, repo, base, project_source = setup_mapping(
        tmp_path, monkeypatch, prompt=project_prompt, remote_url=remote_url)
    for relative in OWNED:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# owned test fixture\n", encoding="utf-8")
    permission_prompt = permission_prefix + ("детали поручения " * 180) + quote + same_message_suffix
    prompts = [("permission-turn", permission_prompt)]
    if duplicate:
        prompts.append(("permission-turn-duplicate", permission_prompt))
    if permission_origin == "agent-relay":
        prompts[0] = (prompts[0][0], "🤖 Сообщение от ИИ через Agent Herder\n" + prompts[0][1])
    prompts.append(("human-turn-1", project_prompt))
    prompts.extend((f"later-{index}", message) for index, message in enumerate(later))
    native_path = Path(base["native_source"])
    _write_native(native_path, workspace, prompts)
    permission_source = _source(prompts[0][1], prompts[0][0])
    # Older LHC records retained only the 2048-byte prefix for this source.
    permission_source.pop("scope_prompt", None)
    if permission_origin == "agent-relay":
        permission_source["origin"] = "agent-relay"
    project_source = {**project_source}
    scope_sources = [permission_source]
    if duplicate:
        scope_sources.append(_source(prompts[1][1], prompts[1][0]))
    scope_sources.append(project_source)
    state_outcome = {
        "id": "current-outcome",
        "owner": {"harness": "codex", "session_id": SID},
        "cwd": str(workspace), "native_source": str(native_path),
        "original_goal": project_prompt, "latest_correction": project_prompt,
        "task_class": "fullcycle", "class_confirmed": True, "contract_confirmed": False,
        "scope_sources": scope_sources,
        "owned_paths": [f"LastHumanCommit/{path}" for path in OWNED],
        "coverage": [], "corrections": [],
        "canary": {"scenario": "LastHumanCommit source", "target": "project:" + str(repo),
                   "expected": "source updated", "status": "pending"},
        "stages": outcome.applicable("fullcycle", project_prompt),
        "revision": outcome.digest([]),
    }
    state = {"schema": 1, "native_entry": {"finish_hold": hold},
             "business": {"runtime": "codex", "transcript_path": str(native_path),
                          "original_prompt": project_prompt, "outcome": state_outcome}}
    state_digest = hashlib.sha256(f"codex\0{SID}".encode()).hexdigest()
    state_path = workspace / ".agents/shared-session/learning" / f"{state_digest}.json"
    state_path.parent.mkdir(parents=True)
    guard.write_state(state_path, state)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return workspace, repo, state_outcome, permission_source, project_source, state_path, state


def resolve(env, quote=PERMISSION):
    workspace, repo, current, permission_source, project_source, _, state = env
    return outcome.resolve_main_permission_source(current, quote, REPOSITORY, "main", state)


def run_contract(env, *, ownership="owned"):
    workspace, repo, current, permission_source, project_source, _, _ = env
    return subprocess.run([
        sys.executable, str(ROOT / "src/common/tools/lhc_outcome.py"),
        "--cwd", str(workspace), "--runtime", "codex", "--session-id", SID, "contract",
        "--product-root", str(repo), "--scope-source", project_source["source"],
        "--scenario", "Only owned LastHumanCommit paths", "--target", "project:" + str(repo),
        "--expected", "the two assigned source files are updated",
        "--owned-path", OWNED[0], "--owned-path", OWNED[1],
        "--integration-branch", "main", "--integration-remote", "origin",
        "--integration-ownership", ownership, "--integration-permission-quote", PERMISSION,
    ], capture_output=True, text=True, env=os.environ.copy())


def test_long_exact_permission_quote_resolves_from_separate_native_source(isolated_tmp_path, monkeypatch):
    env = setup_contract(isolated_tmp_path, monkeypatch)
    workspace, repo, current, permission_source, project_source, _, _ = env

    evidence = resolve(env)
    assert evidence is not None
    assert permission_source["source"] == evidence["source"]
    assert project_source["source"] != evidence["source"]
    assert evidence["index"] < 10
    assert evidence["at"]
    assert len(evidence["sha256"]) == 64
    assert PERMISSION not in permission_source["prompt"]  # Stored scope keeps only a prefix.


def test_contract_keeps_project_source_separate_from_permission_source(isolated_tmp_path, monkeypatch):
    workspace, repo, current, permission_source, project_source, state_path, _ = setup_contract(isolated_tmp_path, monkeypatch)
    result = run_contract((workspace, repo, current, permission_source, project_source, None, None))
    assert result.returncode == 0, result.stderr
    saved = json.loads(result.stdout)["integration_policy"]
    assert saved["main_permission_confirmed"] is True
    assert saved["project_source"] == project_source["source"]
    assert saved["source"] == project_source["source"]
    assert saved["permission_source"] == permission_source["source"]
    assert saved["permission_source_sha256"]
    assert saved["permission_source_index"] < 10
    assert saved["permission_kind"] == "project-universal"
    persisted = guard.load_state(state_path)
    assert outcome._permission_binding_valid(persisted["business"]["outcome"], persisted)


@pytest.mark.parametrize("quote", [
    "Тебе разрешены сделать полностью все действия, включая деплой и мерж в main.",
    "Тебе разрешены мерж в main только для секретаря.",
    "Разрешаю тесты для всех проектов, кроме Airlock, а мерж в main — только для секретаря",
    "Разрешаю все действия для всех проектов, кроме Airlock. Мерж в main только для секретаря",
])
def test_all_actions_or_secretary_only_does_not_grant_all_project_scope(isolated_tmp_path, quote):
    assert not outcome.main_permission({"prompt": quote}, quote, REPOSITORY, "main")


def test_explicit_airlock_exclusion_does_not_authorize_airlock_or_master(isolated_tmp_path):
    assert outcome.main_permission({"prompt": PERMISSION}, PERMISSION, REPOSITORY, "main")
    assert not outcome.main_permission({"prompt": PERMISSION}, PERMISSION, "megamen32/Airlock", "main")
    assert not outcome.main_permission({"prompt": PERMISSION}, PERMISSION, REPOSITORY, "master")


def test_legacy_exact_repository_permission_keeps_terminal_period(isolated_tmp_path):
    quote = "Allow merge megamen32/LastHumanCommit into main."
    assert outcome.main_permission({"prompt": "Implement the work. " + quote}, quote,
                                   REPOSITORY, "main")


def test_quoted_and_negated_scope_is_not_permission(isolated_tmp_path):
    quoted = 'Прочитай цитату: "' + PERMISSION + '".'
    assert not outcome.main_permission({"prompt": quoted}, PERMISSION, REPOSITORY, "main")
    negated = "Тебе не разрешены " + PERMISSION.removeprefix("Тебе разрешены ") + "."
    assert not outcome.main_permission({"prompt": negated}, PERMISSION, REPOSITORY, "main")


def test_resolver_rejects_ambiguous_relay_revoked_and_held_permission(isolated_tmp_path, monkeypatch):
    assert resolve(setup_contract(isolated_tmp_path / "ambiguous", monkeypatch, duplicate=True)) is None
    assert resolve(setup_contract(isolated_tmp_path / "relay", monkeypatch, permission_origin="agent-relay")) is None
    assert resolve(setup_contract(isolated_tmp_path / "revoked", monkeypatch, later=("Не мержи в main в Last Human Commit.",))) is None
    assert resolve(setup_contract(isolated_tmp_path / "held", monkeypatch, hold="PermissionRequest")) is None


def test_project_name_revocation_without_branch_revokes_previous_main_permission(isolated_tmp_path, monkeypatch):
    env = setup_contract(isolated_tmp_path, monkeypatch,
                         later=("Не мержи Last Human Commit.",))
    assert resolve(env) is None


@pytest.mark.parametrize("suffix", [
    ". Do not merge Last Human Commit.",
    ". Не мержи Last Human Commit.",
])
def test_same_native_message_suffix_revokes_universal_permission(isolated_tmp_path, monkeypatch, suffix):
    env = setup_contract(isolated_tmp_path, monkeypatch, same_message_suffix=suffix)
    assert resolve(env) is None


def test_same_native_message_suffix_revokes_exact_repository_permission(isolated_tmp_path, monkeypatch):
    quote = "Allow merge megamen32/LastHumanCommit into main."
    env = setup_contract(isolated_tmp_path, monkeypatch, quote=quote,
                         same_message_suffix=" Do not merge LastHumanCommit.")
    assert resolve(env, quote) is None


@pytest.mark.parametrize("suffix", [
    ". Only after my approval.",
    ". Только после моего подтверждения.",
])
def test_same_native_message_conditional_suffix_does_not_grant(isolated_tmp_path, monkeypatch, suffix):
    env = setup_contract(isolated_tmp_path, monkeypatch, same_message_suffix=suffix)
    assert resolve(env) is None


@pytest.mark.parametrize("revocation", [
    "Спасибо. Не мержи Last Human Commit.",
    "Please do not merge LastHumanCommit.",
])
def test_polite_project_specific_revocation_without_main_is_honored(isolated_tmp_path, monkeypatch, revocation):
    env = setup_contract(isolated_tmp_path, monkeypatch, later=(revocation,))
    assert resolve(env) is None


@pytest.mark.parametrize("later", [
    '“Please do not merge LastHumanCommit.”',
    "Please do not merge LastHumanCommit if the smoke test fails.",
    "🤖 Codex 01a158d0-0f9d-7fa2-9cc3-5ad6fbdb4326 · https://agent.bezrabotnyi.com/#/session/codex%3A01a158d0-0f9d-7fa2-9cc3-5ad6fbdb4326\nPlease do not merge LastHumanCommit.",
])
def test_quoted_conditional_and_relayed_project_text_do_not_revoke(later, isolated_tmp_path, monkeypatch):
    env = setup_contract(isolated_tmp_path, monkeypatch, later=(later,))
    assert resolve(env) is not None


def test_permission_revalidation_observes_later_revocation(isolated_tmp_path, monkeypatch):
    env = setup_contract(isolated_tmp_path, monkeypatch)
    evidence = resolve(env)
    assert evidence is not None
    workspace, repo, current, _, project_source, _, state = env
    policy = {"branch": "main", "remote": "origin", "ownership": "owned",
              "repository": REPOSITORY, "main_permission_confirmed": True,
              "permission_quote": PERMISSION, "permission_source": evidence["source"],
              "permission_source_sha256": evidence["sha256"], "permission_source_index": evidence["index"],
              "permission_source_at": evidence["at"], "permission_kind": evidence["kind"],
              "project_source": project_source["source"]}
    current["integration_policy"] = policy
    current["product_root"] = str(repo)
    current["product_root_source"] = project_source["source"]
    with Path(current["native_source"]).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"type": "response_item", "payload": {
            "type": "message", "role": "user", "content": [{"text": "Не мержи в main в Last Human Commit."}],
            "internal_chat_message_metadata_passthrough": {"turn_id": "later-revoke"}}}, ensure_ascii=False) + "\n")
    assert not outcome._permission_binding_valid(current, state)


def test_permission_revalidation_rejects_changed_source_bytes_and_manual_hold(isolated_tmp_path, monkeypatch):
    env = setup_contract(isolated_tmp_path, monkeypatch)
    workspace, repo, current, permission_source, project_source, _, state = env
    evidence = resolve(env)
    assert evidence
    current["product_root"] = str(repo)
    current["product_root_source"] = project_source["source"]
    current["integration_policy"] = {
        "branch": "main", "remote": "origin", "ownership": "owned", "repository": REPOSITORY,
        "main_permission_confirmed": True, "permission_quote": PERMISSION,
        "permission_source": evidence["source"], "permission_source_sha256": evidence["sha256"],
        "permission_source_index": evidence["index"], "permission_source_at": evidence["at"],
        "permission_kind": evidence["kind"], "project_source": project_source["source"],
    }
    state["native_entry"]["finish_hold"] = "PermissionRequest"
    assert not outcome._permission_binding_valid(current, state)
    state["native_entry"]["finish_hold"] = None
    journal = Path(current["native_source"])
    text = journal.read_text(encoding="utf-8")
    journal.write_text(text.replace(PERMISSION, PERMISSION + " changed", 1), encoding="utf-8")
    assert not outcome._permission_binding_valid(current, state)


def test_wrong_current_repository_and_nonowned_merge_remain_blocked(isolated_tmp_path, monkeypatch):
    env = setup_contract(isolated_tmp_path, monkeypatch, remote_url="https://github.com/other/WrongProject.git")
    evidence = resolve(env)
    assert evidence is not None  # Universal wording alone is broad, but not a project binding.
    workspace, repo, current, _, project_source, _, _ = env
    assert not outcome.product_root_scope_allowed(current, project_source, repo, OWNED)
    assert not outcome.main_permission({"prompt": PERMISSION}, PERMISSION, REPOSITORY, "dev")
    result = run_contract(env)
    assert result.returncode != 0
    assert "external product root" in result.stderr


def test_universal_main_permission_rejects_shared_ownership(isolated_tmp_path, monkeypatch):
    env = setup_contract(isolated_tmp_path, monkeypatch)
    result = run_contract(env, ownership="shared")
    assert result.returncode != 0
    assert "owner-only" in result.stderr
