"""A direct, named project can bind an immediate Git child from accepted proof."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import atexit
import shutil
import subprocess
import sys
import tempfile

import pytest

from _inprocess_lane import prepare_git_template

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_outcome as outcome  # noqa: E402


SESSION_ID = "parent-session"
TURN_ID = "human-turn-1"
REVIEWER_ID = "independent-reviewer"
PUBLISHER_ID = "source-publisher"
REPOSITORY = "megamen32/LastHumanCommit"
PROJECT_ROOT_NAME = "LastHumanCommit"
OWNED = ["src/common/tools/lhc_outcome.py", "tests/test_outcome_contract.py"]


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _git(root: Path, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _rev_parse(root: Path, ref="HEAD"):
    return subprocess.run(["git", "-C", str(root), "rev-parse", ref], check=True,
                          capture_output=True, text=True).stdout.strip()


# One prepared repository per remote URL, copied per case. The history the
# fixture needs is fixed, so it is built once instead of nine `git` calls per
# case: `git init`, two `git config`, two `git add`, two `git commit` and two
# `git rev-parse` all become a copy.
_REPO_TEMPLATES: dict[str, tuple[Path, str, str]] = {}


def _repo_template(remote_url):
    template = _REPO_TEMPLATES.get(remote_url)
    if template is not None:
        return template
    root = Path(tempfile.mkdtemp(prefix="lhc-project-mapping-"))
    atexit.register(shutil.rmtree, root, True)
    _git(root, "init", "-q")
    _git(root, "remote", "add", "origin", remote_url)
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Historical proof fixture")
    (root / "base.txt").write_text("historical base\n", encoding="utf-8")
    _git(root, "add", "base.txt")
    _git(root, "commit", "-qm", "base")
    base = _rev_parse(root)
    for relative in OWNED:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("original published bytes: " + relative + "\n", encoding="utf-8")
    _git(root, "add", *OWNED)
    _git(root, "commit", "-qm", "published source candidate")
    candidate_head = _rev_parse(root)
    prepare_git_template(root)
    template = (root, base, candidate_head)
    _REPO_TEMPLATES[remote_url] = template
    return template


def setup_mapping(tmp_path, monkeypatch, *, prompt=None, repository=REPOSITORY,
                  remote_url="https://github.com/megamen32/LastHumanCommit.git",
                  proof_root=None, accepted=True, ownership=OWNED,
                  root_name=PROJECT_ROOT_NAME):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    repo = workspace / root_name
    repo.mkdir()
    template, base, candidate_head = _repo_template(remote_url)
    shutil.copytree(template, repo, dirs_exist_ok=True)
    for relative in OWNED:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("original published bytes: " + relative + "\n", encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))

    user_prompt = prompt or (
        "Так продолжай и доведи Last Human Commit до рабочего результата. "
        "Исправь оставшуюся проблему с публикацией исходников, проверь через Luna и Sol и установи."
    )
    turn_hash = hashlib.sha256(user_prompt.strip().encode()).hexdigest()[:12]
    parent_native = _write_jsonl(tmp_path / ".codex/sessions/parent.jsonl", [
        {"type": "session_meta", "payload": {"id": SESSION_ID, "cwd": str(workspace)}},
        {"type": "response_item", "payload": {
            "type": "message", "role": "user", "content": [{"text": user_prompt}],
            "internal_chat_message_metadata_passthrough": {"turn_id": TURN_ID}}},
    ])
    source = {
        "source": f"native-user-prompt:{SESSION_ID}:{TURN_ID}:{turn_hash}",
        "origin": "unknown", "prompt": user_prompt[:2048], "scope_prompt": user_prompt,
    }

    publisher_native = _write_jsonl(tmp_path / ".codex/sessions/publisher.jsonl", [
        {"type": "session_meta", "payload": {"id": PUBLISHER_ID, "cwd": str(repo)}}])
    proof_dir = repo / ".tmp/lhc-native-review"
    proof_dir.mkdir(parents=True)
    candidate_root = str(Path(proof_root or repo).resolve())
    published_commit = candidate_head
    owned_hashes = {path: hashlib.sha256((repo / path).read_bytes()).hexdigest() for path in OWNED}
    candidate_body = {
        "root": candidate_root, "repository": repository, "remote": "origin",
        "branch": "main", "ref": "refs/heads/main", "base": base,
        "candidate_head": candidate_head, "owned_files": owned_hashes,
        "permission_source": "native-user-prompt:publisher:source-turn:aaaaaaaaaaaa",
        "permission_quote": "Publish the exact owned candidate from the bound repository to origin/main.",
    }
    fingerprint = hashlib.sha256(json.dumps(candidate_body, sort_keys=True,
                                             separators=(",", ":")).encode()).hexdigest()
    reviewer_rows = [
        {"type": "session_meta", "payload": {"id": REVIEWER_ID, "cwd": str(repo)}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
         "content": [{"text": f"Review source-publication outcome accepted-source-publication candidate {fingerprint} for {repo}."}]}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "phase": "final_answer",
         "content": [{"text": f"APPROVE BOUNDED; scope COVERED; source-ready. Outcome accepted-source-publication candidate {fingerprint}."}]}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
         "content": [{"text": f"Continue outcome accepted-source-publication candidate {fingerprint}; product root {repo}; verify commit {published_commit} on refs/heads/main."}]}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "phase": "final_answer",
         "content": [{"text": f"APPROVE BOUNDED; scope COVERED; source-published. Commit {published_commit} is at refs/heads/main."}]}}]
    reviewer_native = _write_jsonl(tmp_path / ".codex/sessions/reviewer.jsonl", reviewer_rows)
    snapshot = _write_jsonl(proof_dir / "review.jsonl", reviewer_rows)
    manifest_path = proof_dir / "review.manifest.json"
    manifest_path.write_text(json.dumps({
        "format": "agent-herder-transcript-manifest-v1",
        "exporter": "existing-native-review-route",
        "target": {"path": str(snapshot), "harness": "codex", "sessionId": REVIEWER_ID,
                   "complete": True,
                   "source": {"kind": "native-file", "location": str(reviewer_native)}},
    }), encoding="utf-8")
    publication = {
        "schema": "lhc-source-publication-v1", "root": candidate_root,
        "repository": repository, "remote": "origin", "branch": "main",
        "ref": "refs/heads/main", "base": base, "candidate_head": candidate_head,
        "candidate_fingerprint": fingerprint, "published_commit": published_commit,
        "publication_evidence": {"base": base, "commit": published_commit,
                                  "publisher_call": "publish-call", "readback_call": "readback-call",
                                  "ref": "refs/heads/main"},
        "readiness": {"read_calls": list(OWNED), "hash_calls": list(OWNED)},
        "owned_files": owned_hashes,
        "permission_source": "native-user-prompt:publisher:source-turn:aaaaaaaaaaaa",
        "permission_quote": "Publish the exact owned candidate from the bound repository to origin/main.",
    }
    publisher_outcome = {
        "id": "accepted-source-publication", "owner": {"harness": "codex", "session_id": PUBLISHER_ID},
        "cwd": str(repo), "native_source": str(publisher_native),
        "verification_kind": "source-publication", "finish_verdict": "complete",
        "product_verdict": "source-published", "source_publication": publication,
        "integration_policy": {"repository": repository, "remote": "origin", "branch": "main",
                               "ownership": "owned"},
        "stages": {
            "technical": {"status": "complete", "evidence": [{
                "manifest": str(manifest_path), "reviewer": REVIEWER_ID,
                "verification_level": "independent-source-review",
                "source_candidate": fingerprint,
                "source_readiness": {"read_calls": {path: ["read-" + path] for path in OWNED},
                                     "hash_calls": {path: ["hash-" + path] for path in OWNED}}}]},
            "publication": {"status": "complete", "evidence": [{
                "manifest": str(manifest_path), "reviewer": REVIEWER_ID,
                "verification_level": "source-publication-readback",
                "published_commit": published_commit, "ref": "refs/heads/main",
                "expected": "candidate:" + fingerprint, "publisher_call": "publish-call",
                "calls": ["readback-call"]}]},
            "consumer": {"status": "not-applicable", "evidence": []},
            "deploy": {"status": "not-applicable", "evidence": []},
            "integration": {"status": "not-applicable", "evidence": []},
        },
    }
    proof_state = repo / ".agents/shared-session/learning/accepted-source-publication.json"
    proof_state.parent.mkdir(parents=True)
    proof_state.write_text(json.dumps({"business": {"outcome": publisher_outcome}}), encoding="utf-8")

    parent_owned = [f"{root_name}/{path}" for path in ownership]
    current_outcome = {
        "owner": {"harness": "codex", "session_id": SESSION_ID},
        "cwd": str(workspace), "native_source": str(parent_native),
        "owned_paths": parent_owned,
    }
    return workspace, repo, current_outcome, source


def test_direct_project_name_uses_unique_accepted_source_publication_mapping(tmp_path, monkeypatch):
    workspace, repo, current_outcome, source = setup_mapping(tmp_path, monkeypatch)

    assert outcome.product_root_scope_allowed(current_outcome, source, repo, OWNED)
    assert repo.parent == workspace


@pytest.mark.nightly
def test_original_native_receipts_bind_identity_after_mutable_stages_become_pending(tmp_path, monkeypatch):
    workspace, repo, current_outcome, source = setup_mapping(tmp_path, monkeypatch)
    state_path = repo / ".agents/shared-session/learning/accepted-source-publication.json"
    state = json.loads(state_path.read_text())
    saved = state["business"]["outcome"]
    saved["finish_verdict"] = "pending"
    saved["stages"]["technical"]["status"] = "pending"
    saved["stages"]["publication"]["status"] = "pending"
    state_path.write_text(json.dumps(state))

    identity = outcome._verified_historical_source_publication(saved, repo)
    assert identity and identity["candidate"] == saved["source_publication"]["candidate_fingerprint"]
    assert outcome.product_root_scope_allowed(current_outcome, source, repo, OWNED)


@pytest.mark.parametrize("corruption", [
    "candidate", "pathset", "commit", "manifest", "report", "missing-git-object",
    "git-parent", "git-pathset", "git-blob",
])
def test_historical_source_identity_rejects_forged_or_mismatched_receipt(tmp_path, monkeypatch, corruption):
    _, repo, _, _ = setup_mapping(tmp_path, monkeypatch)
    state_path = repo / ".agents/shared-session/learning/accepted-source-publication.json"
    state = json.loads(state_path.read_text())
    saved = state["business"]["outcome"]
    metadata = saved["source_publication"]
    if corruption == "candidate":
        metadata["candidate_fingerprint"] = "f" * 64
    elif corruption == "pathset":
        metadata["owned_files"].pop(OWNED[-1])
    elif corruption == "commit":
        saved["stages"]["publication"]["evidence"][0]["published_commit"] = "4" * 40
    elif corruption == "manifest":
        saved["stages"]["technical"]["evidence"][0]["manifest"] = str(repo / "missing.manifest.json")
    elif corruption == "report":
        manifest = json.loads(Path(saved["stages"]["publication"]["evidence"][0]["manifest"]).read_text())
        snapshot = Path(manifest["target"]["path"])
        rows = [json.loads(line) for line in snapshot.read_text().splitlines()]
        rows[-1]["payload"]["content"][0]["text"] = "APPROVE BOUNDED; scope COVERED; source-published at another commit."
        _write_jsonl(snapshot, rows)
    elif corruption in {"missing-git-object", "git-parent", "git-pathset", "git-blob"}:
        if corruption == "missing-git-object":
            invalid_commit = "4" * 40
        else:
            base = metadata["base"]
            _git(repo, "checkout", "-q", "--detach", base)
            if corruption == "git-parent":
                for index, relative in enumerate(OWNED):
                    target = repo / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("original published bytes: " + relative + "\n", encoding="utf-8")
                    _git(repo, "add", relative)
                    _git(repo, "commit", "-qm", "partial owned delta " + str(index))
            else:
                for relative in OWNED:
                    target = repo / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if corruption == "git-blob":
                        target.write_text("different blob: " + relative + "\n", encoding="utf-8")
                    else:
                        target.write_text("original published bytes: " + relative + "\n", encoding="utf-8")
                if corruption == "git-pathset":
                    (repo / "unowned.txt").write_text("outside owned set\n", encoding="utf-8")
                    _git(repo, "add", *OWNED, "unowned.txt")
                else:
                    _git(repo, "add", *OWNED)
                _git(repo, "commit", "-qm", "invalid historical tree")
            invalid_commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                                            capture_output=True, text=True).stdout.strip()
        metadata["published_commit"] = invalid_commit
        metadata["publication_evidence"]["commit"] = invalid_commit
        saved["stages"]["publication"]["evidence"][0]["published_commit"] = invalid_commit
        manifest = json.loads(Path(saved["stages"]["publication"]["evidence"][0]["manifest"]).read_text())
        snapshot = Path(manifest["target"]["path"])
        source_path = Path(manifest["target"]["source"]["location"])
        rows = [json.loads(line) for line in snapshot.read_text().splitlines()]
        rows[-1]["payload"]["content"][0]["text"] = (
            f"APPROVE BOUNDED; scope COVERED; source-published. Commit {invalid_commit} is at refs/heads/main.")
        _write_jsonl(snapshot, rows)
        _write_jsonl(source_path, rows)

    assert outcome._verified_historical_source_publication(saved, repo) is None


@pytest.mark.nightly
def test_existing_exact_product_root_mapping_reuses_only_its_owned_relative_paths(tmp_path, monkeypatch):
    workspace, repo, current_outcome, source = setup_mapping(tmp_path, monkeypatch)
    current_outcome.update({
        "product_root": str(repo),
        "product_root_source": source["source"],
        "owned_paths": list(OWNED),
    })

    assert outcome.product_root_scope_allowed(current_outcome, source, repo, OWNED)
    assert not outcome.product_root_scope_allowed(
        current_outcome, source, repo, [*OWNED, "src/new-unowned.py"])
    wrong_source = {**source, "source": "native-user-prompt:other:turn:aaaaaaaaaaaa"}
    assert not outcome.product_root_scope_allowed(current_outcome, wrong_source, repo, OWNED)
    neighbor = workspace / "LastHumanCommit-copy"
    neighbor.mkdir()
    assert not outcome.product_root_scope_allowed(current_outcome, source, neighbor, OWNED)


@pytest.mark.parametrize("prompt", [
    "Please finish the quote ‘Last Human Commit’ someday.",
    "Do not edit Last Human Commit.",
    "Do not work in Last Human Commit; preserve its files.",
    "Fix Last Human; the larger LastHumanCommitment is unrelated.",
    "Status of Last Human Commit?",
])
def test_project_mapping_rejects_quoted_negated_partial_or_status_mentions(tmp_path, monkeypatch, prompt):
    workspace, repo, current_outcome, source = setup_mapping(tmp_path, monkeypatch, prompt=prompt)
    assert not outcome.product_root_scope_allowed(current_outcome, source, repo, OWNED)


def test_project_mapping_rejects_agent_relay_even_when_it_names_the_project(tmp_path, monkeypatch):
    workspace, repo, current_outcome, source = setup_mapping(
        tmp_path, monkeypatch,
        prompt="🤖 Сообщение от ИИ через Agent Herder\nПожалуйста, исправь Last Human Commit.")
    source["origin"] = "agent-relay"
    assert not outcome.product_root_scope_allowed(current_outcome, source, repo, OWNED)


def test_project_mapping_requires_owned_paths_from_current_task_scope(tmp_path, monkeypatch):
    workspace, repo, current_outcome, source = setup_mapping(tmp_path, monkeypatch)
    assert not outcome.product_root_scope_allowed(
        current_outcome, source, repo, [*OWNED, "src/unassigned.py"])
    assert not outcome.product_root_scope_allowed(current_outcome, source, repo, ["../neighbor/file.py"])


@pytest.mark.nightly
def test_project_mapping_deduplicates_equivalent_accepted_publication_receipts(tmp_path, monkeypatch):
    workspace, repo, current_outcome, source = setup_mapping(tmp_path, monkeypatch)
    learning = repo / ".agents/shared-session/learning"
    original = learning / "accepted-source-publication.json"
    (learning / "accepted-source-publication-repeated.json").write_bytes(original.read_bytes())

    assert outcome.product_root_scope_allowed(current_outcome, source, repo, OWNED)


def test_forged_conflicting_publication_record_does_not_override_verified_identity(tmp_path, monkeypatch):
    workspace, repo, current_outcome, source = setup_mapping(tmp_path, monkeypatch)
    learning = repo / ".agents/shared-session/learning"
    original = learning / "accepted-source-publication.json"
    conflicting = json.loads(original.read_text())
    proof = conflicting["business"]["outcome"]
    proof["source_publication"]["repository"] = "other/LastHumanCommit"
    proof["integration_policy"]["repository"] = "other/LastHumanCommit"
    (learning / "conflicting-accepted-publication.json").write_text(json.dumps(conflicting))

    # The edited lookalike no longer matches the immutable candidate digest;
    # it is not a second accepted identity and cannot make the verified receipt
    # ambiguous.
    assert outcome.product_root_scope_allowed(current_outcome, source, repo, OWNED)


@pytest.mark.parametrize("fault", ["wrong_remote", "wrong_repository", "wrong_root", "unaccepted", "missing_manifest"])
def test_project_mapping_rejects_untrusted_or_stale_repository_proof(tmp_path, monkeypatch, fault):
    kwargs = {}
    if fault == "wrong_remote":
        kwargs["remote_url"] = "https://github.com/other/LastHumanCommit.git"
    workspace, repo, current_outcome, source = setup_mapping(tmp_path, monkeypatch, **kwargs)
    state_path = repo / ".agents/shared-session/learning/accepted-source-publication.json"
    saved = json.loads(state_path.read_text())
    proof = saved["business"]["outcome"]
    if fault == "wrong_repository":
        proof["source_publication"]["repository"] = "other/LastHumanCommit"
        proof["integration_policy"]["repository"] = "other/LastHumanCommit"
    elif fault == "wrong_root":
        proof["source_publication"]["root"] = str(workspace / "neighbor")
    elif fault == "unaccepted":
        proof["product_verdict"] = "source-ready"
    elif fault == "missing_manifest":
        proof["stages"]["technical"]["evidence"][0]["manifest"] = str(repo / ".tmp/missing.json")
    state_path.write_text(json.dumps(saved), encoding="utf-8")
    assert not outcome.product_root_scope_allowed(current_outcome, source, repo, OWNED)


def test_project_mapping_rejects_duplicate_fullname_children_and_symlink_alias(tmp_path, monkeypatch):
    workspace, repo, current_outcome, source = setup_mapping(tmp_path, monkeypatch)
    alias = workspace / "last human commit"
    alias.symlink_to(repo, target_is_directory=True)
    assert not outcome.product_root_scope_allowed(current_outcome, source, repo, OWNED)


def test_project_mapping_rejects_symlink_root_argument_even_with_unrelated_alias_name(tmp_path, monkeypatch):
    workspace, repo, current_outcome, source = setup_mapping(tmp_path, monkeypatch)
    alias = workspace / "checkout-alias"
    alias.symlink_to(repo, target_is_directory=True)
    assert not outcome.product_root_scope_allowed(current_outcome, source, alias, OWNED)


def test_project_mapping_rejects_nested_copy_even_with_matching_proof(tmp_path, monkeypatch):
    workspace, repo, current_outcome, source = setup_mapping(tmp_path, monkeypatch)
    nested = workspace / "apps" / PROJECT_ROOT_NAME
    nested.mkdir(parents=True)
    _git(nested, "init", "-q")
    _git(nested, "remote", "add", "origin", "https://github.com/megamen32/LastHumanCommit.git")
    assert not outcome.product_root_scope_allowed(current_outcome, source, nested, OWNED)
