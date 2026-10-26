"""Bounded source-only candidate and publication proof regressions."""
import atexit
import shutil
import subprocess
import sys
import tempfile
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "src/common/tools"
sys.path.insert(0, str(TOOLS))
import lhc_source_publication as source_pub
import lhc_outcome_review as review
import lhc_outcome as outcome
import lhc_time_guard as guard

from _inprocess_lane import prepare_git_template
from _repos import head_of, prepared_repo


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


# One prepared product checkout and one prepared bare remote, copied per case.
# The history and the identity of the fixture are fixed, so `git init`, both
# `git config` calls, `git add`, `git commit` and the bare `git init` all
# become a copy; only the real publication work stays a real Git call.
#
# The remote and the branch it carries are part of the prepared checkout as
# well: `git remote add` and `git push -u` are a copy too, so the case only
# has to name the bare remote it copied in the configuration of its checkout.
_REPO_TEMPLATE: Path | None = None
_BARE_TEMPLATE: Path | None = None


def _templates() -> tuple[Path, Path]:
    """The prepared product checkout and the prepared bare remote."""
    global _REPO_TEMPLATE, _BARE_TEMPLATE
    if _REPO_TEMPLATE is None:
        root = Path(tempfile.mkdtemp(prefix="lhc-source-publication-"))
        atexit.register(shutil.rmtree, root, True)
        bare = root / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
        prepare_git_template(bare)
        product = prepared_repo(
            root / "product",
            config=(("user.email", "test@example.invalid"),
                    ("user.name", "Test")),
            files=(("owned.py", "print('base')\n"),), message="base")
        git(product, "remote", "add", "origin", str(bare))
        git(product, "push", "-q", "-u", "origin", "HEAD:main")
        _BARE_TEMPLATE = bare
        _REPO_TEMPLATE = product
    return _REPO_TEMPLATE, _BARE_TEMPLATE


def _name_own_remote(root: Path, bare: Path, template: Path) -> None:
    """Name the bare remote of this case in the configuration of its checkout.

    ``git remote add`` writes the URL of the remote into the configuration of
    the repository.  The prepared checkout carries that section already, with
    the URL of the prepared remote; the case names the bare remote it copied.
    """
    config = root / ".git" / "config"
    text = config.read_text(encoding="utf-8")
    assert text.count(str(template)) == 1, text
    config.write_text(text.replace(str(template), str(bare)), encoding="utf-8")


def repository(tmp_path):
    root = tmp_path / "product"
    root.mkdir()
    template, bare_template = _templates()
    shutil.copytree(template, root, dirs_exist_ok=True)
    bare = tmp_path / "remote.git"
    shutil.copytree(bare_template, bare, dirs_exist_ok=True)
    _name_own_remote(root, bare, bare_template)
    return root, bare


def scope(root):
    return ("Source-only task. Publish owned.py from " + str(root) +
            " to origin/main.")


def capture(root, bare, *, prompt=None, target=None, expected="candidate", paths=None,
            scope_check=lambda *_: True, canary_target=None):
    source = {"source": "native-user-prompt:publisher:source-1",
              "scope_prompt": prompt if prompt is not None else scope(root)}
    return source_pub.capture_contract(
        {"owner": {"session_id": "publisher"}}, source, root,
        paths if paths is not None else ["owned.py"], "origin", "main",
        None, canary_target if canary_target is not None else "project:" + str(root),
        target if target is not None else "git ls-remote origin refs/heads/main",
        expected, scope_check)


def observation(call_id, command, output, root, *, exit_code=0, at="2026-10-20T20:00:00+00:00"):
    return ({"call_id": call_id, "arguments": {"cmd": command, "workdir": str(root)},
             "_native_cwd": str(root), "_exit_code": exit_code, "_source_time": at}, output)


def test_source_readiness_requires_full_owned_file_read_and_exact_hash(tmp_path):
    root, bare = repository(tmp_path)
    (root / "owned.py").write_text("print('candidate')\n")
    metadata = capture(root, bare)
    content = (root / "owned.py").read_text()
    digest = metadata["owned_files"]["owned.py"]
    observations = [
        observation("read", "cat owned.py", content, root),
        observation("hash", "sha256sum owned.py", f"{digest}  owned.py\n", root),
    ]

    assert source_pub.source_readiness(metadata, observations, root)["read_calls"] == {"owned.py": "read"}
    with pytest.raises(ValueError, match="full-file reads and matching hash"):
        source_pub.source_readiness(metadata, observations[:1], root)

    wrong_hash = [observations[0], observation("wrong", "sha256sum owned.py", "0" * 64 + "  owned.py\n", root)]
    with pytest.raises(ValueError, match="full-file reads and matching hash"):
        source_pub.source_readiness(metadata, wrong_hash, root)


def test_source_readiness_reuses_one_identical_body_with_explicit_aliases_and_hashes_each_path(tmp_path):
    root, bare = repository(tmp_path)
    content = "print('candidate')\n"
    (root / "owned.py").write_text(content)
    (root / "alias.py").write_text(content)
    metadata = capture(root, bare, paths=["owned.py", "alias.py"],
                       prompt=("Source-only task. Publish owned.py and alias.py from " + str(root) +
                               " to origin/main."))
    digest = metadata["owned_files"]["owned.py"]
    assert metadata["owned_files"]["alias.py"] == digest
    evidence = [
        observation("one-body", "cat owned.py", content, root),
        observation("both-hashes", "sha256sum owned.py alias.py",
                    f"{digest}  owned.py\n{digest}  alias.py\n", root),
    ]
    readiness = source_pub.source_readiness(metadata, evidence, root)
    assert readiness["read_calls"] == {"owned.py": "one-body", "alias.py": "one-body"}
    assert readiness["read_aliases"] == {"owned.py": "owned.py", "alias.py": "owned.py"}
    assert readiness["hash_calls"] == {"owned.py": "both-hashes", "alias.py": "both-hashes"}
    with pytest.raises(ValueError, match="matching hash evidence"):
        source_pub.source_readiness(metadata, evidence[:1], root)


def test_contract_binds_exact_scope_ref_and_candidate_bytes(tmp_path):
    root, bare = repository(tmp_path)
    (root / "owned.py").write_text("print('candidate')\n")
    metadata = capture(root, bare)
    assert metadata["ref"] == "refs/heads/main"
    assert metadata["candidate_fingerprint"]

    with pytest.raises(ValueError, match="imperative publish/push assignment"):
        capture(root, bare, prompt="Source-only task. Do not publish owned.py from " + str(root) + " to origin/main.")
    with pytest.raises(ValueError, match="imperative publish/push assignment"):
        capture(root, bare, prompt="Source-only task. Publish owned.py from " + str(root) + " to origin/main.evil.")
    with pytest.raises(ValueError, match="target must explicitly bind"):
        capture(root, bare, target="project:" + str(root))
    with pytest.raises(ValueError, match="exact current native assignment"):
        capture(root, bare, scope_check=lambda *_: False)
    outside = tmp_path / "outside.py"
    outside.write_text("outside\n")
    (root / "linked.py").symlink_to(outside)
    with pytest.raises(ValueError, match="cannot traverse symlinks"):
        capture(root, bare, paths=["linked.py"],
                prompt="Source-only task. Publish linked.py from " + str(root) + " to origin/main.")
    with pytest.raises(ValueError, match="imperative publish/push assignment"):
        capture(root, bare, paths=["unowned.py"], prompt=(
            "Source-only task. Publish owned.py from " + str(root) +
            " to origin/main. Do not touch unowned.py."))

    (root / "owned.py").write_text("changed after contract\n")
    with pytest.raises(ValueError, match="bytes changed after contract"):
        source_pub.source_readiness(metadata, [], root)


@pytest.mark.nightly
def test_publication_needs_native_push_then_current_ref_and_exact_blobs(tmp_path):
    root, bare = repository(tmp_path)
    (root / "owned.py").write_text("print('candidate')\n")
    metadata = capture(root, bare)
    git(root, "commit", "-aqm", "candidate")
    git(root, "push", "-q", "origin", "HEAD:main")
    commit = head_of(root)
    native_path = tmp_path / "publisher.jsonl"
    native_path.write_text("\n".join([
        '{"type":"session_meta","payload":{"id":"publisher","cwd":"' + str(root) + '"}}',
        '{"type":"event_msg","timestamp":"2026-10-20T20:01:00+00:00","payload":{"type":"item_completed","item":{"type":"CommandExecution","id":"push-1","exit_code":0,"cwd":"' + str(root) + '","command":["git","push","origin","HEAD:refs/heads/main"]}}}',
    ]) + "\n")
    outcome = {"owner": {"session_id": "publisher"}, "cwd": str(root), "native_source": str(native_path)}
    readback = subprocess.run(["git", "-C", str(root), "ls-remote", "origin", "refs/heads/main"],
                              check=True, capture_output=True, text=True).stdout
    observations = [observation("remote", "git ls-remote origin refs/heads/main", readback, root,
                                at="2026-10-20T20:02:00+00:00")]
    proof = source_pub.publication_readback(metadata, observations, root, outcome,
                                           "2026-10-20T20:00:00+00:00")
    assert proof["commit"] == commit
    assert proof["publisher_call"] == "push-1"

    (root / "follow-up.txt").write_text("remote moved after reviewer readback\n")
    git(root, "add", "follow-up.txt")
    git(root, "commit", "-qm", "move remote after readback")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/main")
    with pytest.raises(ValueError, match="remote ref changed after the native readback"):
        source_pub.publication_readback(metadata, observations, root, outcome,
                                        "2026-10-20T20:00:00+00:00")

    native_path.write_text(native_path.read_text().replace('"exit_code":0', '"exit_code":1'))
    with pytest.raises(ValueError, match="successful current native git push"):
        source_pub.publication_readback(metadata, observations, root, outcome,
                                        "2026-10-20T20:00:00+00:00")


def test_source_review_recognizes_bounded_approval_and_keeps_later_negative(tmp_path):
    assert review.source_report_result("APPROVE BOUNDED; scope covered") == (False, True)
    assert review.source_report_result("Not approved: missing owned file") == (True, False)
    assert review.source_report_result("Not approved: hashes matched, but authorization is missing.") == (True, False)
    assert review.source_report_result("REVISE: hashes matched, but the remote is wrong.") == (True, False)
    outcome = {"verification_kind": "source-publication", "source_publication": {},
               "scope_sources": [], "corrections": []}
    assert review.own_assessment(outcome, "Not approved: missing owned file", [], tmp_path)


def test_large_file_native_chunks_reassemble_exact_candidate_and_flow_to_review(tmp_path):
    root, bare = repository(tmp_path)
    content = "".join(f"{index:04d}: " + "x" * 90 + "\n" for index in range(1, 804))
    (root / "owned.py").write_text(content)
    metadata = capture(root, bare)
    lines = content.splitlines(keepends=True)
    reads = []
    chunk_ids = []
    start = 1
    while start <= len(lines):
        end = start + 299
        call_id = f"chunk-{start}"
        output = "".join(lines[start - 1:end])
        reads.append(observation(call_id, f"sed -n '{start},{end}p' owned.py", output, root,
                                 at=f"2026-10-20T20:00:{len(reads):02d}+00:00"))
        chunk_ids.append(call_id)
        start = end + 1
    digest = metadata["owned_files"]["owned.py"]
    hash_call = observation("whole-file-hash", "sha256sum owned.py", f"{digest}  owned.py\n", root,
                            at="2026-10-20T20:00:10+00:00")
    observations = [*reads, hash_call]
    readiness = source_pub.source_readiness(metadata, observations, root,
                                            floor="2026-10-20T19:59:00+00:00")
    assert readiness["read_calls"]["owned.py"] == chunk_ids

    scope_source = {"source": metadata["permission_source"], "scope_prompt": scope(root)}
    review_outcome = {"verification_kind": "source-publication", "source_publication": metadata,
        "scope_sources": [scope_source], "corrections": [], "id": "chunked-outcome",
        "original_goal": "Source-only publish owned.py", "owned_paths": ["owned.py"],
        "canary": {"target": "project:" + str(root), "scenario": "Source readiness",
                   "expected": "candidate source is ready"}}
    report = review.raw_review(review_outcome, "APPROVE BOUNDED; scope covered", observations, root)
    cited = report["stages"]["technical"]["evidence_calls"]
    assert set(cited) == {*chunk_ids, "whole-file-hash"}


def test_large_file_chunks_reject_gaps_overlap_wrong_file_truncation_and_stale_parts(tmp_path):
    root, bare = repository(tmp_path)
    content = "".join(f"{index:04d}: " + "y" * 90 + "\n" for index in range(1, 604))
    (root / "owned.py").write_text(content)
    metadata = capture(root, bare)
    lines = content.splitlines(keepends=True)
    chunks = []
    for start in (1, 301, 601):
        end = start + 299
        chunks.append(observation(f"chunk-{start}", f"sed -n '{start},{end}p' owned.py",
                                  "".join(lines[start - 1:end]), root,
                                  at="2026-10-20T20:00:01+00:00"))
    digest = metadata["owned_files"]["owned.py"]
    hash_call = observation("hash", "sha256sum owned.py", f"{digest}  owned.py\n", root,
                            at="2026-10-20T20:00:04+00:00")
    floor = "2026-10-20T20:00:00+00:00"
    invalid_sets = [
        [chunks[0], chunks[2], hash_call],
        [chunks[0], observation("overlap", "sed -n '300,599p' owned.py",
                                "".join(lines[299:599]), root), chunks[2], hash_call],
        [chunks[0], observation("wrong-file", "sed -n '301,600p' another.py",
                                "".join(lines[300:600]), root), chunks[2], hash_call],
        [chunks[0], observation("cropped", "sed -n '301,600p' owned.py",
                                "... command output truncated for persistence ...", root), chunks[2], hash_call],
        [observation("stale", "sed -n '1,300p' owned.py", "".join(lines[:300]), root,
                     at="2026-10-20T19:59:59+00:00"), chunks[1], chunks[2], hash_call],
    ]
    for evidence in invalid_sets:
        with pytest.raises(ValueError, match="full-file reads and matching hash"):
            source_pub.source_readiness(metadata, evidence, root, floor=floor)


@pytest.mark.parametrize("chunked", [False, True])
def test_standalone_truncation_marker_inside_exact_candidate_is_valid_content(tmp_path, chunked):
    root, bare = repository(tmp_path)
    content = b"heading\n... command output truncated for persistence ...\nbody\n"
    (root / "owned.py").write_bytes(content)
    metadata = capture(root, bare)
    digest = metadata["owned_files"]["owned.py"]
    if chunked:
        read_calls = [observation("standalone-marker-chunk", "sed -n '1,300p' owned.py",
                                  content.decode(), root)]
    else:
        read_calls = [observation("standalone-marker-cat", "cat owned.py", content.decode(), root)]
    evidence = [*read_calls, observation("standalone-marker-hash", "sha256sum owned.py",
                                         f"{digest}  owned.py\n", root)]
    readiness = source_pub.source_readiness(metadata, evidence, root)
    assert readiness["read_calls"]["owned.py"]


def test_native_read_cap_still_rejects_oversized_single_body(tmp_path):
    root, bare = repository(tmp_path)
    content = b"x" * 65536
    (root / "owned.py").write_bytes(content)
    metadata = capture(root, bare)
    digest = metadata["owned_files"]["owned.py"]
    evidence = [observation("oversized-body", "cat owned.py", content.decode(), root),
                observation("oversized-hash", "sha256sum owned.py", f"{digest}  owned.py\n", root)]
    with pytest.raises(ValueError, match="full-file reads and matching hash"):
        source_pub.source_readiness(metadata, evidence, root)


def test_same_native_scope_revocation_cancels_earlier_publish_clause(tmp_path):
    root, bare = repository(tmp_path)
    permission = "Source-only task. Publish owned.py from " + str(root) + " to origin/main."
    source = {"source": "native-user-prompt:publisher:source-1", "scope_prompt": permission}
    metadata = source_pub.capture_contract(
        {"owner": {"session_id": "publisher"}}, source, root, ["owned.py"], "origin", "main",
        None, "project:" + str(root), "git ls-remote origin refs/heads/main", "candidate", lambda *_: True)
    assert source_pub.permission_unchanged(metadata, source)

    source["scope_prompt"] = permission + " Do not publish."
    assert not source_pub.permission_unchanged(metadata, source)

    permission += " Do not publish."
    with pytest.raises(ValueError, match="imperative publish/push assignment"):
        capture(root, bare, prompt=permission)


@pytest.mark.parametrize("ending", ["but publication is paused", "but publication is on hold",
                                    "but publication is cancelled", "but publication is revoked"])
def test_same_clause_publication_hold_cancels_publish_permission(tmp_path, ending):
    root, bare = repository(tmp_path)
    prompt = ("Source-only task. Publish owned.py from " + str(root) +
              " to origin/main, " + ending + ".")
    with pytest.raises(ValueError, match="imperative publish/push assignment"):
        capture(root, bare, prompt=prompt)


@pytest.mark.nightly
def test_publication_rejects_extra_unowned_commit_path(tmp_path):
    root, bare = repository(tmp_path)
    (root / "owned.py").write_text("print('candidate')\n")
    metadata = capture(root, bare)
    (root / "owned.py").write_text("print('candidate')\n")
    (root / "unowned.txt").write_text("outside assignment\n")
    git(root, "add", "owned.py", "unowned.txt")
    git(root, "commit", "-qm", "candidate plus unowned path")
    git(root, "push", "-q", "origin", "HEAD:main")
    native_path = tmp_path / "publisher.jsonl"
    native_path.write_text("\n".join([
        '{"type":"session_meta","payload":{"id":"publisher","cwd":"' + str(root) + '"}}',
        '{"type":"event_msg","timestamp":"2026-10-20T20:01:00+00:00","payload":{"type":"item_completed","item":{"type":"CommandExecution","id":"push-1","exit_code":0,"cwd":"' + str(root) + '","command":["git","push","origin","HEAD:refs/heads/main"]}}}',
    ]) + "\n")
    outcome = {"owner": {"session_id": "publisher"}, "cwd": str(root), "native_source": str(native_path)}
    readback = subprocess.run(["git", "-C", str(root), "ls-remote", "origin", "refs/heads/main"],
                              check=True, capture_output=True, text=True).stdout
    observations = [observation("remote", "git ls-remote origin refs/heads/main", readback, root,
                                at="2026-10-20T20:02:00+00:00")]
    with pytest.raises(ValueError, match="outside or missing from the exact owned set"):
        source_pub.publication_readback(metadata, observations, root, outcome,
                                        "2026-10-20T20:00:00+00:00")


@pytest.mark.nightly
def test_public_cli_contract_review_keeps_publication_pending_then_completes(tmp_path, monkeypatch, capsys):
    session_root = tmp_path / "session"
    session_root.mkdir()
    product_root, bare = repository(tmp_path)
    (product_root / "owned.py").write_text("print('candidate')\n")
    original_goal = "Implement the source release, deploy the application, and verify the consumer flow."
    goal = ("Source-only publication. No merge, deployment, runtime actions, product/provider calls, "
            "source edits or subagents. Publish the exact owned.py from " + str(product_root) + " to origin/main.")
    source_id = "native-user-prompt:publisher:assigned-turn:" + hashlib.sha256(goal.encode()).hexdigest()[:12]
    source = {"source": source_id, "prompt": goal, "scope_prompt": goal}
    codex_home = tmp_path / ".codex"
    sessions = codex_home / "sessions"
    sessions.mkdir(parents=True)
    publisher_path = sessions / "publisher.jsonl"
    publisher_path.write_text(json.dumps({"type": "session_meta", "payload": {
        "id": "publisher", "cwd": str(session_root)}}) + "\n" +
        json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user",
                  "content": [{"text": original_goal}], "internal_chat_message_metadata_passthrough": {
                      "turn_id": "original-turn"}}}) + "\n" +
        json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user",
                  "content": [{"text": goal}], "internal_chat_message_metadata_passthrough": {
                      "turn_id": "assigned-turn"}}}) + "\n")
    stages = outcome.applicable("fullcycle", original_goal)
    assert stages["deploy"]["status"] == "pending"
    legacy_outcome = {"id": "source-outcome", "task_class": "quickfix",
        "canary": {"scenario": "Source-only readiness", "target": "project:" + str(product_root),
                   "expected": "candidate source is ready"},
        "original_goal": goal, "corrections": [], "owned_paths": ["owned.py"],
        "product_root": str(product_root), "stages": stages}
    with pytest.raises(ValueError, match="project target needs one scope-named native CLI"):
        review.raw_review(legacy_outcome, "PASS; source-only candidate is ready", [], product_root)
    state_path = guard.learning_path(session_root, "codex", "publisher")
    state = {"business": {"runtime": "codex", "transcript_path": str(publisher_path),
        "original_prompt": original_goal, "outcome": {
            "id": "source-outcome", "owner": {"harness": "codex", "session_id": "publisher"},
            "cwd": str(session_root), "native_source": str(publisher_path), "scope_sources": [source],
            "original_goal": original_goal, "latest_correction": goal, "task_class": "fullcycle",
            "started_at": "2026-10-20T19:00:00+00:00", "contract_confirmed": False,
            "class_confirmed": False, "owned_paths": [], "coverage": [], "corrections": [goal],
            "canary": {"scenario": "Source-only readiness", "target": "FEEDBACK.md",
                       "expected": "candidate source is ready", "status": "pending"},
            "stages": stages, "revision": outcome.digest([]), "evidence_after": "2026-10-20T19:00:00+00:00"}}}
    guard.write_state(state_path, state)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(outcome, "remote_binding", lambda *_: "owner/repository")

    contract_args = ["--cwd", str(session_root), "--runtime", "codex", "--session-id", "publisher",
        "contract", "--verification-kind", "source-publication", "--scope-source", source_id,
        "--scenario", "Source-only readiness", "--target", "project:" + str(product_root),
        "--expected", "candidate source is ready", "--product-root", str(product_root),
        "--owned-path", "owned.py", "--integration-remote", "origin", "--integration-branch", "main",
        "--integration-ownership", "owned", "--stage-target", "publication=git ls-remote origin refs/heads/main",
        "--stage-expected", "publication=candidate"]
    original_scope = source["scope_prompt"]
    mixed_scope = ("Source-only publication. Publish the exact owned.py from " + str(product_root) +
                   " to origin/main and deploy the application.")
    source["scope_prompt"] = source["prompt"] = mixed_scope
    guard.write_state(state_path, state)
    monkeypatch.setattr(sys, "argv", ["lhc_outcome.py", *contract_args])
    with pytest.raises(ValueError, match="cannot omit deployment still required"):
        outcome.main()
    capsys.readouterr()
    source["scope_prompt"] = source["prompt"] = original_scope
    guard.write_state(state_path, state)
    monkeypatch.setattr(sys, "argv", ["lhc_outcome.py", *contract_args])
    outcome.main()
    capsys.readouterr()
    current = guard.load_state(state_path)["business"]["outcome"]
    assert current["verification_kind"] == "source-publication"
    assert current["stages"]["consumer"]["status"] == "not-applicable"
    assert current["stages"]["deploy"]["status"] == "not-applicable"
    assert current["stages"]["integration"]["status"] == "not-applicable"
    assert current["stages"]["publication"]["status"] == "pending"

    def reviewer_manifest(reviewer_id, *, stale=False, include_remote=False, final=None,
                          native_id=None, later_negative=False, include_readiness=True):
        path = sessions / (reviewer_id + ".jsonl")
        current_time = datetime.now(timezone.utc) + timedelta(seconds=2)
        now = current_time.isoformat()
        old = (current_time - timedelta(hours=2)).isoformat()
        stamp = old if stale else now
        current_candidate = current["source_publication"]["candidate_fingerprint"]
        rows = [{"type": "session_meta", "timestamp": stamp, "payload": {
            "id": native_id or reviewer_id, "cwd": str(product_root)}},
            {"type": "response_item", "timestamp": stamp, "payload": {"type": "message", "role": "user",
             "content": [{"text": f"Independent review of source-publication outcome {current['id']} "
                                   f"candidate {current_candidate} for product root {product_root}. "
                                   f"Original task: {original_goal}. Current scope: {goal}."}]}}]
        call_ids = []
        def call(call_id, command, output, *, at=stamp):
            call_ids.append(call_id)
            rows.extend([
                {"type": "response_item", "timestamp": at, "payload": {"type": "function_call",
                 "name": "exec_command", "call_id": call_id,
                 "arguments": json.dumps({"cmd": command, "workdir": str(product_root)})}},
                {"type": "response_item", "timestamp": at, "payload": {"type": "function_call_output",
                 "call_id": call_id, "output": output}},
            ])
        content = (product_root / "owned.py").read_text()
        digest = source_pub._sha(content.encode())
        if include_readiness:
            call("read-owned", "cat owned.py", content)
            call("hash-owned", "sha256sum owned.py", f"{digest}  owned.py\n")
        if include_remote:
            remote = subprocess.run(["git", "-C", str(product_root), "ls-remote", "origin", "refs/heads/main"],
                                    check=True, capture_output=True, text=True).stdout
            call("remote-readback", "git ls-remote origin refs/heads/main", remote,
                     at=(current_time + timedelta(seconds=2)).isoformat())
        report = final or (f"APPROVE BOUNDED; scope covered; source-ready outcome {current['id']} "
                           f"candidate {current_candidate}.")
        rows.append({"type": "response_item", "timestamp": (current_time + timedelta(seconds=3)).isoformat(),
                     "payload": {"type": "message", "role": "assistant", "phase": "final",
                                 "content": [{"text": report}]}})
        if later_negative:
            rows.append({"type": "response_item", "timestamp": (current_time + timedelta(seconds=4)).isoformat(),
                         "payload": {"type": "message", "role": "assistant", "phase": "final",
                                     "content": [{"text": "Not approved: the latest review found a source defect."}]}})
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        review_dir = product_root / ".tmp/lhc-native-review"
        review_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = review_dir / (reviewer_id + ".snapshot.jsonl")
        snapshot_path.write_bytes(path.read_bytes())
        manifest = review_dir / (reviewer_id + ".manifest.json")
        manifest.write_text(json.dumps({"format": "agent-herder-transcript-manifest-v1", "target": {
            "path": str(snapshot_path), "harness": "codex", "complete": True, "sessionId": native_id or reviewer_id,
            "source": {"kind": "native-file", "location": str(path)}}}))
        return manifest

    def reject_manifest(manifest, *, expected=None):
        before = guard.load_state(state_path)
        monkeypatch.setattr(sys, "argv", ["lhc_outcome.py", "--cwd", str(session_root), "--runtime", "codex",
                                          "--session-id", "publisher", "review", "--manifest", str(manifest)])
        with pytest.raises(ValueError, match=expected or ".+"):
            outcome.main()
        capsys.readouterr()
        assert guard.load_state(state_path) == before

    wrong_paths = [*contract_args]
    wrong_paths[wrong_paths.index("owned.py")] = "unowned.py"
    monkeypatch.setattr(sys, "argv", ["lhc_outcome.py", *wrong_paths])
    before = guard.load_state(state_path)
    with pytest.raises(ValueError, match="external product root needs the exact native assignment"):
        outcome.main()
    capsys.readouterr()
    assert guard.load_state(state_path) == before

    technical_manifest = reviewer_manifest("reviewer-tech")
    _, _, technical_observations = review.load_review(technical_manifest)
    assert technical_observations, "fixture native calls must be parsed as observations"
    monkeypatch.setattr(sys, "argv", ["lhc_outcome.py", "--cwd", str(session_root), "--runtime", "codex",
                                      "--session-id", "publisher", "review", "--manifest", str(technical_manifest)])
    outcome.main()
    capsys.readouterr()
    current = guard.load_state(state_path)["business"]["outcome"]
    assert current["product_verdict"] == "source-ready"
    assert current["stages"]["technical"]["status"] == "complete"
    assert current["stages"]["publication"]["status"] == "pending"
    original_technical_evidence = json.loads(json.dumps(current["stages"]["technical"]["evidence"]))
    persisted = guard.load_state(state_path)
    reused = review._reusable_source_readiness(current, persisted, session_root)
    assert reused == current["stages"]["technical"]["evidence"][0]["source_readiness"]
    remote_changed = json.loads(json.dumps(current))
    remote_changed["integration_policy"]["remote"] = "new-remote"
    assert review._reusable_source_readiness(remote_changed, persisted, session_root) == reused

    reject_manifest(reviewer_manifest("owner-self", native_id="publisher"),
                    expected="review must be independent")
    reject_manifest(reviewer_manifest("stale-review", stale=True))
    reject_manifest(reviewer_manifest("later-negative", later_negative=True))
    assert current["canary"]["status"] == "pending"

    git(product_root, "commit", "-aqm", "candidate source")
    git(product_root, "push", "-q", "origin", "HEAD:refs/heads/main")
    push_time = datetime.now(timezone.utc) + timedelta(seconds=2)
    with publisher_path.open("a") as stream:
        stream.write(json.dumps({"type": "event_msg", "timestamp": push_time.isoformat(),
            "payload": {"type": "item_completed", "item": {"type": "CommandExecution", "id": "publisher-push",
            "exit_code": 0, "cwd": str(product_root), "command": ["git", "push", "origin", "HEAD:refs/heads/main"]}}}) + "\n")
    commit = head_of(product_root)
    published_manifest = reviewer_manifest("reviewer-published", include_remote=True, include_readiness=False,
        final=(f"APPROVE BOUNDED; scope covered; source-published outcome {current['id']} candidate "
               f"{current['source_publication']['candidate_fingerprint']}. Published commit {commit} at refs/heads/main."))
    monkeypatch.setattr(sys, "argv", ["lhc_outcome.py", "--cwd", str(session_root), "--runtime", "codex",
                                      "--session-id", "publisher", "review", "--manifest", str(published_manifest)])
    outcome.main()
    capsys.readouterr()
    current = guard.load_state(state_path)["business"]["outcome"]
    assert current["product_verdict"] == "source-published"
    assert current["stages"]["publication"]["status"] == "complete"
    assert current["stages"]["technical"]["evidence"] == original_technical_evidence
    assert current["canary"]["status"] == "complete"

    # A delivered source candidate is a historical result. Later repository
    # edits and administrative traffic must not reopen it or rewrite its receipt.
    accepted_snapshot = json.loads(json.dumps(current))
    _tech = current["stages"]["technical"]["evidence"][0]
    _pub = current["stages"]["publication"]["evidence"][0]
    assert outcome._valid_publication_manifest(product_root, _tech["manifest"], _tech["reviewer"], outcome_id=current["id"], candidate=current["source_publication"]["candidate_fingerprint"], report_kind="source-ready")
    assert outcome._valid_publication_manifest(product_root, _pub["manifest"], _pub["reviewer"], outcome_id=current["id"], candidate=current["source_publication"]["candidate_fingerprint"], published_commit=current["source_publication"]["published_commit"], ref=current["source_publication"]["ref"], report_kind="source-published")
    assert outcome._verified_historical_source_publication(current, product_root), "accepted fixture must carry a verifiable immutable receipt"
    state_after_delivery = guard.load_state(state_path)
    (product_root / "owned.py").write_text("print('later repository change')\n")
    observe_time = datetime.now(timezone.utc) + timedelta(minutes=1)
    observed = outcome.observe(
        state_after_delivery,
        {"prompt": "Status: is the delivered source publication still complete?"},
        "UserPromptSubmit", session_root, "publisher", observe_time,
    )
    assert observed == accepted_snapshot
    assert observed["finish_verdict"] == "complete"
    assert observed["source_publication"]["published_commit"] == commit
    held_state = guard.load_state(state_path)
    held_state["native_entry"] = {"finish_hold": "Interrupt"}
    held = outcome.observe(
        held_state,
        {"prompt": "Status: is the delivered source publication still complete?"},
        "UserPromptSubmit", session_root, "publisher", observe_time + timedelta(seconds=1),
    )
    assert held["finish_verdict"] == "blocked"
    assert held["stages"]["publication"]["status"] == "complete"

    # A previously reopened row is recovered only from its original paired
    # candidate receipts; its newer floor stays in place.
    stale_state = guard.load_state(state_path)
    stale_outcome = stale_state["business"]["outcome"]
    stale_outcome["stages"]["technical"]["status"] = "pending"
    stale_outcome["stages"]["publication"]["status"] = "pending"
    stale_outcome["canary"]["status"] = "pending"
    stale_outcome["finish_verdict"] = "pending"
    stale_floor = (observe_time + timedelta(seconds=5)).isoformat()
    stale_outcome["evidence_after"] = stale_floor
    stale_outcome["revision"] = outcome.scope_revision(stale_outcome, session_root)
    stale_outcome["stage_fingerprints"] = outcome.stage_contract_fingerprints(stale_outcome)
    recovered = outcome.observe(
        stale_state,
        {"prompt": "Status: is the previously published candidate still complete?"},
        "UserPromptSubmit", session_root, "publisher", observe_time + timedelta(seconds=6),
    )
    assert recovered["finish_verdict"] == "complete"
    assert recovered["revision"] == accepted_snapshot["revision"]
    assert recovered["evidence_after"] == stale_floor
    assert recovered["stages"]["technical"]["evidence"] == accepted_snapshot["stages"]["technical"]["evidence"]
    assert recovered["stages"]["publication"]["evidence"] == accepted_snapshot["stages"]["publication"]["evidence"]

    # A new direct requirement is effective and reopens the affected outcome.
    changed_scope_state = guard.load_state(state_path)
    changed_scope = outcome.observe(
        changed_scope_state,
        {"prompt": "Deploy the source artifact and verify the consumer flow."},
        "UserPromptSubmit", session_root, "publisher", observe_time + timedelta(seconds=1),
    )
    assert changed_scope["latest_correction"] == "Deploy the source artifact and verify the consumer flow."
    assert changed_scope["contract_confirmed"] is False
    assert changed_scope["evidence_after"] == (observe_time + timedelta(seconds=1)).isoformat()

    # A source-published label without both bound native receipts is not a seal.
    false_receipt_state = guard.load_state(state_path)
    false_outcome = false_receipt_state["business"]["outcome"]
    false_outcome["stages"]["publication"]["evidence"] = []
    before_false_receipt = json.loads(json.dumps(false_outcome))
    (product_root / "owned.py").write_text("print('another repository change')\n")
    unsealed = outcome.observe(
        false_receipt_state,
        {"prompt": "Status: is this still complete?"},
        "UserPromptSubmit", session_root, "publisher", observe_time + timedelta(seconds=2),
    )
    assert unsealed != before_false_receipt
    assert unsealed["stages"]["publication"]["status"] == "pending"
