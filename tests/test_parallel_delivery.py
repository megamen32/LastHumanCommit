"""Behavioral acceptance for file-per-message coordination, not prompt keywords."""
import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))

def module():
    import lhc_chat
    return lhc_chat

def test_parallel_writers_and_independent_readers(tmp_path):
    chat = module()
    with ThreadPoolExecutor(max_workers=12) as pool:
        messages = list(pool.map(lambda i: chat.send(tmp_path, "codex:worker-"+str(i), "message "+str(i)), range(60)))
    assert len({m["id"] for m in messages}) == 60
    assert len(list((tmp_path/"chat").glob("*.json"))) == 60
    read = []
    while batch := chat.read_new(tmp_path, "reader-a", limit=7):
        read.extend(batch)
    assert {m["id"] for m in read} == {m["id"] for m in messages}
    assert chat.read_new(tmp_path, "reader-a") == []
    assert len(chat.read_new(tmp_path, "reader-b", limit=100)) == 60

def test_retry_does_not_overwrite_and_late_publish_is_not_lost(tmp_path):
    chat = module()
    first = chat.send(tmp_path, "claude:a", "first", message_id="stable-a")
    assert chat.send(tmp_path, "claude:a", "first", message_id="stable-a") == first
    with pytest.raises(ValueError):
        chat.send(tmp_path, "claude:a", "different", message_id="stable-a")
    assert len(chat.read_new(tmp_path, "reader")) == 1
    chat.send(tmp_path, "codex:b", "late writer", message_id="000-before-other-filenames")
    assert [x["text"] for x in chat.read_new(tmp_path, "reader")] == ["late writer"]

def test_recipient_and_malformed_files(tmp_path):
    chat = module()
    chat.send(tmp_path, "sender", "private", recipient="a")
    chat.send(tmp_path, "sender", "broadcast")
    (tmp_path/"chat"/"corrupt.json").write_text("not json")
    assert [m["text"] for m in chat.read_new(tmp_path, "b")] == ["broadcast"]
    assert {m["text"] for m in chat.read_new(tmp_path, "a")} == {"broadcast", "private"}
    for bad in ["../outside", "", "a/b"]:
        with pytest.raises(ValueError):
            chat.send(tmp_path, "sender", "x", message_id=bad)

def test_worktrees_share_project_chat(tmp_path):
    chat = module()
    project = tmp_path/"project"
    project.mkdir()
    def git(*args):
        return subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True, text=True)
    git("init", "-b", "main"); git("config", "user.email", "test@example.invalid"); git("config", "user.name", "Test")
    (project/"README").write_text("base"); git("add", "README"); git("commit", "-m", "base")
    worktree = tmp_path/"worker"
    git("worktree", "add", "-b", "worker", str(worktree))
    assert chat.project_root(worktree) == project
    assert chat.state_root(worktree) == chat.state_root(project)

def test_entry_is_small_automatic_and_does_not_write_state(tmp_path):
    import lhc_entry
    before = list(tmp_path.iterdir())
    context = lhc_entry.context_for({"session_id":"a", "cwd":str(tmp_path)}, ROOT)
    assert str(ROOT/"AGENTS.md") in context
    assert len(context) < 2200
    assert list(tmp_path.iterdir()) == before

def test_native_instruction_bootstrap_is_idempotent_and_preserves_other_rules(tmp_path):
    spec = importlib.util.spec_from_file_location("lhc_install", ROOT/"plugins/last-human-commit/scripts/install_runtime.py")
    install = importlib.util.module_from_spec(spec); spec.loader.exec_module(install)
    target=tmp_path/".codex/AGENTS.md"; target.parent.mkdir()
    target.write_text("Keep my project limits.\n<!-- ogsd-autoentry:begin -->old GSD<!-- ogsd-autoentry:end -->\n")
    root=ROOT/"plugins/last-human-commit"
    first=install.configure(tmp_path,root,"codex",True)
    assert first["changed"] and Path(first["backup"]).is_file()
    assert "Keep my project limits." in target.read_text()
    assert "old GSD" not in target.read_text()
    assert "native LHC hook" in target.read_text()
    assert str(root) not in target.read_text(), "Codex must not pin a second cache version"
    assert install.configure(tmp_path,root,"codex",True)["changed"] is False
