"""A native assignment can inspect an explicit product checkout elsewhere."""
import json
import hashlib
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/common/tools"))
import lhc_outcome as outcome
import lhc_outcome_review as review
import lhc_time_guard as guard


def native_source(tmp_path, prompt, operations, *, sid="worker", cwd=None):
    """Write a small Codex source with its user assignment and actual calls."""
    path = tmp_path / ".codex/sessions/worker.jsonl"
    path.parent.mkdir(parents=True)
    rows = [
        {"type": "session_meta", "payload": {"id": sid, "cwd": str(cwd or tmp_path)}},
        {"type": "response_item", "payload": {
            "type": "message", "role": "user", "content": [{"text": prompt}],
            "internal_chat_message_metadata_passthrough": {"turn_id": "assigned-turn"}}},
    ]
    rows.extend(operations)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return path


def brief_read(brief_path, body, *, workdir, exit_code=0, command=None, extra_argv=(), append_rules=False):
    output = body + ("\n# Agent Rules\nNo additional assignment" if append_rules else "")
    return [{"type": "event_msg", "payload": {"type": "item_completed", "item": {
        "type": "CommandExecution", "id": "read-brief", "exit_code": exit_code,
        "command": ["/bin/bash", "-lc", command or f"cat {brief_path}", *extra_argv],
        "cwd": "file://" + str(workdir), "aggregated_output": output}}}]


def cli(tmp_path, cwd, *args):
    return subprocess.run(
        [sys.executable, str(Path(outcome.__file__).resolve()), "--cwd", str(cwd),
         "--runtime", "codex", "--session-id", "worker", *args],
        capture_output=True, text=True,
        env={**os.environ, "HOME": str(tmp_path / "home"), "CODEX_HOME": str(tmp_path / ".codex")})


def stored_assignment(tmp_path):
    session_root = tmp_path / "session"
    product_root = tmp_path / "product"
    session_root.mkdir()
    product_root.mkdir()
    subprocess.run(["git", "init", "-q", str(session_root)], check=True)
    subprocess.run(["git", "init", "-q", str(product_root)], check=True)
    (product_root / "owned.py").write_text("print('before')\n")
    brief = session_root / ".agents/tasks/briefs/20261020-parallel-u53.md"
    scope_prompt = f"Execute the exact paths in {brief} in {product_root}."
    prompt = ("<agent-herder-coordination board=\"test\">Allow owned userio merge into main. Do not publish. " +
              "metadata " * 400 + "</agent-herder-coordination>\n" + scope_prompt)
    body = ("# U53 source lane\n\nCanonical checkout: " + str(product_root) +
            "\nExclusive writable paths:\n- owned.py\n\nTask and acceptance:\nScope")
    source_path = native_source(tmp_path, prompt, brief_read(brief, body, workdir=session_root),
                                sid="worker", cwd=session_root)
    source = {"source": "native-user-prompt:worker:assigned-turn:" + hashlib.sha256(prompt.strip().encode()).hexdigest()[:12],
              "prompt": prompt.strip()[:2048], "scope_prompt": scope_prompt}
    stages = {stage: {"status": "pending", "basis": "task-class:quickfix", "evidence": []}
              for stage in outcome.STAGES}
    stages["technical"] = {"status": "complete", "basis": "prior", "evidence": ["old-call"]}
    state = {"business": {"runtime": "codex", "transcript_path": str(source_path),
                           "original_prompt": prompt,
                           "outcome": {"id": "outcome-one", "owner": {"harness": "codex", "session_id": "worker"},
                                       "cwd": str(session_root), "native_source": str(source_path),
                                       "scope_sources": [source], "original_goal": prompt,
                                       "latest_correction": scope_prompt, "task_class": "quickfix",
                                       "contract_confirmed": False, "class_confirmed": False,
                                       "owned_paths": [], "coverage": [], "corrections": [],
                                       "canary": {"scenario": "Run owned CLI", "target": "project:" + str(session_root),
                                                  "expected": "prints before", "status": "complete"},
                                       "stages": stages, "revision": outcome.digest([]),
                                       "evidence_after": "before-contract"}}}
    state_path = guard.learning_path(session_root, "codex", "worker")
    guard.write_state(state_path, state)
    return session_root, product_root, source, state_path


def test_product_revision_reads_owned_files_from_explicit_product_root(tmp_path):
    session_root = tmp_path / "session"
    product_root = tmp_path / "product"
    session_root.mkdir()
    product_root.mkdir()
    (product_root / "owned.py").write_text("print('product')\n")
    contract = {
        "original_goal": "Implement the assigned source files.",
        "corrections": [],
        "owned_paths": ["owned.py"],
        "product_root": str(product_root),
    }

    expected = outcome.digest([("owned.py", outcome.native.file_hash(product_root, "owned.py"))])
    assert outcome.scope_revision(contract, session_root) == expected


def test_product_root_rejects_owned_symlink_that_escapes_checkout(tmp_path):
    product_root = tmp_path / "product"
    outside = tmp_path / "outside.py"
    product_root.mkdir()
    outside.write_text("print('outside')\n")
    (product_root / "owned.py").symlink_to(outside)
    contract = {"original_goal": "Implement owned.py", "corrections": [],
                "owned_paths": ["owned.py"], "product_root": str(product_root)}

    with pytest.raises(ValueError, match="outside product root"):
        outcome.product_paths(contract, tmp_path / "session")


def test_legacy_absolute_owned_path_is_kept_only_when_contained(tmp_path):
    product_root = tmp_path / "product"
    product_root.mkdir()
    owned = product_root / "owned.py"
    owned.write_text("print('inside')\n")
    contract = {"original_goal": "Implement owned.py", "corrections": [],
                "owned_paths": [str(owned)]}

    assert outcome.product_paths(contract, product_root) == [str(owned)]
    contract["owned_paths"] = [str(tmp_path / "outside.py")]
    with pytest.raises(ValueError, match="outside product root"):
        outcome.product_paths(contract, product_root)


def test_external_product_root_requires_exact_native_assignment_and_original_brief_read(tmp_path, monkeypatch):
    session_root = tmp_path / "session"
    product_root = tmp_path / "product"
    session_root.mkdir()
    product_root.mkdir()
    owned = ["src/owned.py", "tests/test_owned.py"]
    brief = session_root / ".agents/tasks/briefs/20261020-parallel-u53.md"
    prompt = f"Execute the exact paths in {brief} in {product_root}."
    body = ("# U53 parallel source lane\n\nOwning project: UserIO\nCanonical checkout: " + str(product_root) +
            "\nExclusive writable paths:\n" + "\n".join("- " + p for p in owned) + "\n\nTask and acceptance:\nMore scope")
    native_path = native_source(
        tmp_path,
        prompt,
        brief_read(brief, body, workdir=session_root),
        sid="worker",
        cwd=session_root,
    )
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    brief.parent.mkdir(parents=True)
    brief.write_text("# changed assignment\nCanonical checkout: /elsewhere\n")
    source = {"source": "native-user-prompt:worker:assigned-turn:" + hashlib.sha256(prompt.strip().encode()).hexdigest()[:12],
              "prompt": prompt}
    contract = {"owner": {"harness": "codex", "session_id": "worker"},
                "cwd": str(session_root), "native_source": str(native_path)}

    assert outcome.product_root_scope_allowed(contract, source, product_root, owned)


@pytest.mark.parametrize("fault", ["wrong-root", "missing-path", "failed-read", "wrong-session", "wrong-cwd",
                                    "wrong-heading", "duplicate-root", "echo-command", "later-document-block"])
def test_external_product_root_denies_unbound_or_failed_native_assignment(tmp_path, fault, monkeypatch):
    session_root = tmp_path / "session"
    product_root = tmp_path / "product"
    session_root.mkdir()
    product_root.mkdir()
    owned = ["src/owned.py", "tests/test_owned.py"]
    brief = session_root / ".agents/tasks/briefs/20261020-parallel-u53.md"
    prompt = f"Execute the exact paths in {brief} in {product_root}."
    call_root = tmp_path / "foreign" if fault == "wrong-cwd" else session_root
    call_paths = owned[:1] if fault == "missing-path" else owned
    body = ("# U53 parallel source lane\n\nOwning project: UserIO\nCanonical checkout: " + str(product_root if fault != "wrong-root" else tmp_path / "foreign") +
            "\nExclusive writable paths:\n" + "\n".join("- " + p for p in call_paths) + "\n\nTask and acceptance:\nMore scope")
    if fault == "wrong-heading":
        body = body.replace("# U53 parallel source lane", "# S42 source lane")
    if fault == "duplicate-root":
        body = body.replace("\nExclusive writable paths:", "\nCanonical checkout: " + str(product_root) + "\nExclusive writable paths:")
    if fault == "later-document-block":
        body = ("# U53 parallel source lane\n\nNo ownership data here.\n# Project State\nCanonical checkout: " +
                str(product_root) + "\nExclusive writable paths:\n" + "\n".join("- " + p for p in owned))
    native_path = native_source(
        tmp_path,
        prompt,
        brief_read(brief, body, workdir=call_root, exit_code=1 if fault == "failed-read" else 0,
                   command=(f"echo '{body}' && cat {brief}" if fault == "echo-command" else
                            f"cat {brief} && cat .planning/STATE.md" if fault == "later-document-block" else None)),
        sid="somebody-else" if fault == "wrong-session" else "worker",
        cwd=session_root,
    )
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    source = {"source": "native-user-prompt:worker:assigned-turn:" + hashlib.sha256(prompt.strip().encode()).hexdigest()[:12],
              "prompt": prompt}
    contract = {"owner": {"harness": "codex", "session_id": "worker"},
                "cwd": str(session_root), "native_source": str(native_path)}

    assert not outcome.product_root_scope_allowed(contract, source, product_root, owned)


def test_native_brief_scope_rejects_extra_bash_argv_even_when_argv2_is_cat(tmp_path, monkeypatch):
    session_root = tmp_path / "session"
    product_root = tmp_path / "product"
    session_root.mkdir()
    product_root.mkdir()
    owned = ["src/owned.py"]
    brief = session_root / ".agents/tasks/briefs/20261020-parallel-s42.md"
    prompt = f"Execute the exact paths in {brief}; the assignment states the product root."
    body = ("# S42 parallel source lane\nCanonical checkout: " + str(product_root) +
            "\nExclusive writable paths:\n- src/owned.py\n")
    native_path = native_source(
        tmp_path, prompt,
        brief_read(brief, body, workdir=session_root, command="printf harmless", extra_argv=(f"cat {brief}",)),
        sid="worker", cwd=session_root)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    source = {"source": "native-user-prompt:worker:assigned-turn:" + hashlib.sha256(prompt.strip().encode()).hexdigest()[:12],
              "prompt": prompt, "scope_prompt": prompt}
    contract = {"owner": {"harness": "codex", "session_id": "worker"},
                "cwd": str(session_root), "native_source": str(native_path)}

    assert not outcome.product_root_scope_allowed(contract, source, product_root, owned)


@pytest.mark.parametrize("brief_first", [False, True])
def test_compound_native_reads_cannot_attribute_root_paths_to_named_brief(tmp_path, monkeypatch, brief_first):
    session_root = tmp_path / "session"
    product_root = tmp_path / "product"
    session_root.mkdir()
    product_root.mkdir()
    owned = ["src/owned.py"]
    brief = session_root / ".agents/tasks/briefs/20261020-parallel-s42.md"
    prompt = f"Execute the exact paths in {brief}; the assignment states the product root."
    task = "# S42 parallel source lane\n"
    unrelated = ("Canonical checkout: " + str(product_root) +
                 "\nExclusive writable paths:\n- src/owned.py\n")
    if brief_first:
        output = task + "Brief contains no ownership fields.\n" + unrelated + "# Project State\nState\n"
        command = f"cat {brief} && cat .planning/STATE.md"
    else:
        output = ("# Agent Rules\nRules\n# S42 example\n" + unrelated +
                  "# Project State\nState\n")
        command = f"cat .agents/AGENTS.md && cat {brief} && cat .planning/STATE.md"
    native_path = native_source(tmp_path, prompt,
                                brief_read(brief, output, workdir=session_root, command=command),
                                sid="worker", cwd=session_root)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    source = {"source": "native-user-prompt:worker:assigned-turn:" + hashlib.sha256(prompt.strip().encode()).hexdigest()[:12],
              "prompt": prompt, "scope_prompt": prompt}
    contract = {"owner": {"harness": "codex", "session_id": "worker"},
                "cwd": str(session_root), "native_source": str(native_path)}

    assert not outcome.product_root_scope_allowed(contract, source, product_root, owned)


def test_s42_bounded_sed_standalone_brief_read_binds_its_assignment(tmp_path, monkeypatch):
    session_root = tmp_path / "session"
    product_root = tmp_path / "agent-herder"
    session_root.mkdir()
    product_root.mkdir()
    owned = ["src/integrator-transcript.ts", "tests/integrator-transcript.test.ts", "docs/integrator-transcript.md"]
    brief = session_root / ".agents/tasks/briefs/20261020-parallel-s42.md"
    prompt = f"Execute the exact paths in {brief}; the assignment states the product root."
    body = ("# S42 parallel source lane\nCanonical checkout: " + str(product_root) +
            "\nExclusive writable paths:\n" + "\n".join("- " + p for p in owned) +
            "\nTask details\n")
    command = f"sed -n '1,160p' {brief.relative_to(session_root)}"
    native_path = native_source(tmp_path, prompt,
                                brief_read(brief, body, workdir=session_root, command=command, append_rules=False),
                                sid="worker", cwd=session_root)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    source = {"source": "native-user-prompt:worker:assigned-turn:" + hashlib.sha256(prompt.strip().encode()).hexdigest()[:12],
              "prompt": prompt, "scope_prompt": prompt}
    contract = {"owner": {"harness": "codex", "session_id": "worker"},
                "cwd": str(session_root), "native_source": str(native_path)}

    assert outcome.product_root_scope_allowed(contract, source, product_root, owned)


def test_contract_cli_binds_external_root_without_moving_session_state(tmp_path):
    session_root, product_root, source, state_path = stored_assignment(tmp_path)
    command = ["contract", "--scenario", "Run owned CLI", "--target", "project:" + str(product_root),
               "--expected", "prints before", "--scope-source", source["source"],
               "--product-root", str(product_root), "--owned-path", "owned.py"]

    result = cli(tmp_path, session_root, *command)
    assert result.returncode == 0, result.stderr
    saved = json.loads(state_path.read_text())["business"]["outcome"]
    expected_revision = outcome.digest([("owned.py", outcome.native.file_hash(product_root, "owned.py"))])
    assert saved["cwd"] == str(session_root)
    assert saved["product_root"] == str(product_root)
    assert saved["owned_paths"] == ["owned.py"]
    assert saved["revision"] == expected_revision
    assert saved["evidence_after"] != "before-contract"
    assert saved["stages"]["technical"]["status"] == "pending"
    assert saved["canary"]["status"] == "pending"

    before = saved["revision"]
    outcome.observe(json.loads(state_path.read_text()), {}, "Stop", session_root, "worker", datetime.now(timezone.utc))
    after_state = json.loads(state_path.read_text())
    after = outcome.observe(after_state, {}, "Stop", session_root, "worker", datetime.now(timezone.utc))["revision"]
    assert after == before
    status = cli(tmp_path, session_root, "status")
    assert status.returncode == 0, status.stderr
    assert json.loads(status.stdout)["product_root"] == str(product_root)
    assert json.loads(status.stdout)["revision"] == before


def test_missing_session_root_has_precise_error_and_creates_no_new_state(tmp_path):
    session_root, product_root, _, state_path = stored_assignment(tmp_path)
    wrong_root = cli(tmp_path, product_root, "status")

    assert wrong_root.returncode != 0
    assert "no LHC session state for codex/worker" in wrong_root.stderr
    assert "no state was created" in wrong_root.stderr
    assert state_path.is_file()
    assert not (product_root / ".agents/shared-session/learning").exists()

    nested_cwd = session_root / "different-cwd"
    nested_cwd.mkdir()
    reused_state = cli(tmp_path, nested_cwd, "status")
    assert reused_state.returncode != 0
    assert f"bound to session root {session_root}" in reused_state.stderr


def test_herder_board_metadata_cannot_mark_publication_excluded(tmp_path):
    session_root, product_root, source, state_path = stored_assignment(tmp_path)
    result = cli(tmp_path, session_root, "contract", "--scenario", "Run owned CLI",
                 "--target", "project:" + str(product_root), "--expected", "prints before",
                 "--scope-source", source["source"], "--product-root", str(product_root),
                 "--owned-path", "owned.py", "--not-applicable", "publication")

    assert result.returncode != 0
    assert "N/A needs explicit original/latest scope" in result.stderr
    saved = json.loads(state_path.read_text())["business"]["outcome"]
    assert saved["stages"]["publication"]["status"] == "pending"


def test_herder_board_metadata_cannot_authorize_a_main_merge(tmp_path):
    session_root, product_root, source, state_path = stored_assignment(tmp_path)
    subprocess.run(["git", "-C", str(product_root), "remote", "add", "origin",
                    "https://github.com/owned/userio.git"], check=True)
    result = cli(tmp_path, session_root, "contract", "--scenario", "Run owned CLI",
                 "--target", "project:" + str(product_root), "--expected", "prints before",
                 "--scope-source", source["source"], "--product-root", str(product_root),
                 "--owned-path", "owned.py", "--integration-branch", "main",
                 "--integration-remote", "origin", "--integration-ownership", "owned",
                 "--integration-permission-quote", "Allow owned userio merge into main.")

    assert result.returncode == 0, result.stderr
    policy = json.loads(state_path.read_text())["business"]["outcome"]["integration_policy"]
    assert policy["repository"] == "owned/userio"
    assert not policy["main_permission_confirmed"]
    assert not policy["target_scope_confirmed"]


def test_reviewer_keeps_native_cwd_but_product_command_needs_explicit_product_workdir(tmp_path):
    session_root = tmp_path / "reviewer-session"
    product_root = tmp_path / "product"
    session_root.mkdir()
    product_root.mkdir()
    (product_root / "owned.py").write_text("print('ready')\n")
    explicit = {"name": "exec_command", "call_id": "with-workdir",
                "arguments": json.dumps({"cmd": "python3 owned.py", "workdir": str(product_root)}),
                "_native_cwd": str(session_root), "_exit_code": 0}
    implicit = {"name": "exec_command", "call_id": "without-workdir",
                "arguments": json.dumps({"cmd": "python3 owned.py"}),
                "_native_cwd": str(session_root), "_exit_code": 0}

    assert review.real_observation(explicit, "ready\n", "python3 owned.py", "consumer", "quickfix", product_root)
    assert not review.real_observation(implicit, "ready\n", "python3 owned.py", "consumer", "quickfix", product_root)
