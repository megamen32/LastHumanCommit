"""The last questions of the canon that still started a process.

Two questions of the production code of the canon are answered from the
state the repository keeps on disk instead of from a process:

* the **diff** - which paths differ between the working tree, the index and
  a revision.  The observer of the milestone asks it on every observation,
  and the reuse of an own testing report asks it for the delta of a
  baseline;
* the **plan tools** - the collector of the leaves and the renderer of the
  page.  The hook runs them when the agent writes a leaf.

These cases hold two things at once:

* the **budget** - how many processes the code under test may start, and
* the **answer** - the answer of the module is the answer of Git, byte for
  byte, for every shape of a repository the module reads.
"""
import contextlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src" / "common" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import lhc_entry as entry  # noqa: E402  (the tools import each other by name)
import lhc_milestone as native  # noqa: E402


# The budget of the questions of this file.  The diff is read from the tree
# of the revision, from the index and from the working tree; the plan tools
# run in the process that asks them.  Neither of them starts a process.
DIFF_BUDGET = 0
PLAN_BUDGET = 0


@contextlib.contextmanager
def processes():
    """Every process the code under test starts, in order."""
    started = []
    original_run = subprocess.run
    original_popen = subprocess.Popen

    def counted_run(command, *args, **kwargs):
        started.append([str(part) for part in command] if isinstance(command, (list, tuple))
                       else [str(command)])
        return original_run(command, *args, **kwargs)

    def counted_popen(command, *args, **kwargs):
        started.append([str(part) for part in command] if isinstance(command, (list, tuple))
                       else [str(command)])
        return original_popen(command, *args, **kwargs)

    subprocess.run = counted_run
    subprocess.Popen = counted_popen
    try:
        yield started
    finally:
        subprocess.run = original_run
        subprocess.Popen = original_popen


def git(root, *args):
    """Git itself, for the answers the cases compare against."""
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    return result.stdout if result.returncode == 0 else b""


def repository(path):
    """A Git checkout of its own, the way the observer meets one."""
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    return path


def commit_all(root, message="base"):
    git(root, "add", "-A")
    git(root, "-c", "user.email=observer@example.test", "-c", "user.name=Observer",
        "commit", "-qm", message)


def head_of(root):
    """The commit of HEAD, read from the repository itself."""
    gitdir = Path(root) / ".git"
    head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref:"):
        return head
    name = head[4:].strip()
    loose = gitdir / name
    if loose.is_file():
        return loose.read_text(encoding="utf-8").strip()
    for line in (gitdir / "packed-refs").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == name:
            return parts[0]
    raise AssertionError("HEAD names no commit: " + name)


def write(root, name, text):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# The shapes of a repository the module reads
# ---------------------------------------------------------------------------


def build_base(path):
    """The repository every shape starts from: two committed files."""
    root = repository(path)
    write(root, "page.html", "<main>one</main>")
    write(root, "app.js", "const a = 1;")
    commit_all(root)
    # ``git init`` writes fourteen sample hooks that no case ever runs, and
    # this repository is copied once per shape.  They are four times heavier
    # than the rest of it; the default ignore rules in ``info/exclude`` stay
    # untouched, so the checkout behaves exactly as before.
    hooks = Path(root) / ".git" / "hooks"
    if hooks.is_dir():
        for sample in hooks.glob("*.sample"):
            sample.unlink()
    return root


def shape_modified(root):
    write(root, "page.html", "<main>two</main>")


def shape_modified_in_a_subdirectory(root):
    write(root, "sub/page.html", "<main>two</main>")


def shape_deleted(root):
    os.remove(Path(root) / "page.html")


def shape_deleted_in_the_index(root):
    git(root, "rm", "-q", "page.html")


def shape_deleted_but_kept_in_the_worktree(root):
    git(root, "rm", "-q", "--cached", "page.html")


def shape_added_in_the_index(root):
    write(root, "new.html", "<main>new</main>")
    git(root, "add", "new.html")


def shape_added_and_then_gone(root):
    write(root, "new.html", "<main>new</main>")
    git(root, "add", "new.html")
    os.remove(Path(root) / "new.html")


def shape_untracked(root):
    write(root, "extra.html", "<main>extra</main>")


def shape_staged_and_reverted(root):
    write(root, "page.html", "<main>staged</main>")
    git(root, "add", "page.html")
    write(root, "page.html", "<main>one</main>")


def shape_mode_changed(root):
    os.chmod(Path(root) / "page.html", 0o755)


def shape_mode_changed_without_the_mode(root):
    git(root, "config", "core.fileMode", "false")
    os.chmod(Path(root) / "page.html", 0o755)


def shape_symlink(root):
    os.symlink("page.html", Path(root) / "link.html")
    git(root, "add", "-A")


def shape_symlink_committed(root):
    os.symlink("page.html", Path(root) / "link.html")
    commit_all(root, "link")


def shape_symlink_changed(root):
    shape_symlink_committed(root)
    os.remove(Path(root) / "link.html")
    os.symlink("app.js", Path(root) / "link.html")


def shape_renamed_in_the_index(root):
    git(root, "mv", "page.html", "renamed.html")


def shape_renamed_in_the_worktree(root):
    os.rename(Path(root) / "page.html", Path(root) / "renamed.html")


def shape_added_and_deleted(root):
    git(root, "rm", "-q", "page.html")
    write(root, "new.html", "<main>new</main>")
    git(root, "add", "new.html")


def shape_attributes(root):
    write(root, ".gitattributes", "*.html text\n")


def shape_attributes_and_a_change(root):
    shape_attributes(root)
    write(root, "page.html", "<main>two</main>")


def shape_second_commit(root):
    write(root, "second.html", "<main>second</main>")
    commit_all(root, "second")


def shape_packed(root):
    git(root, "gc", "-q")


SHAPES = [
    shape_modified,
    shape_modified_in_a_subdirectory,
    shape_deleted,
    shape_deleted_in_the_index,
    shape_deleted_but_kept_in_the_worktree,
    shape_added_in_the_index,
    shape_added_and_then_gone,
    shape_untracked,
    shape_staged_and_reverted,
    shape_mode_changed,
    shape_mode_changed_without_the_mode,
    shape_symlink,
    shape_symlink_committed,
    shape_symlink_changed,
    shape_renamed_in_the_index,
    shape_renamed_in_the_worktree,
    shape_added_and_deleted,
    shape_attributes,
    shape_attributes_and_a_change,
    shape_second_commit,
    shape_packed,
]


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    """One committed repository every shape starts from."""
    return build_base(tmp_path_factory.mktemp("base") / "repo")


def shape_repository(tmp_path, base, function):
    """A copy of the base repository with one shape applied to it."""
    root = tmp_path / "repo"
    shutil.copytree(base, root, symlinks=True)
    function(root)
    return root


# ---------------------------------------------------------------------------
# The diff
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("function", SHAPES, ids=lambda function: function.__name__)
def test_the_answer_of_the_module_is_the_answer_of_git(tmp_path, base, function):
    """The listing of the changed paths is Git's listing, byte for byte."""
    root = shape_repository(tmp_path, base, function)
    head = head_of(root)
    questions = [
        (["diff", "--name-only", "-z", head], ["diff", "--name-only", "-z", head]),
        (["diff", "--cached", "--name-only", "-z", head], ["diff", "--cached", "--name-only", "-z", head]),
        (["diff", "--name-only", "-z"], ["diff", "--name-only", "-z"]),
    ]
    for wanted_args, asked_args in questions:
        assert native.git(root, *asked_args) == git(root, *wanted_args), asked_args


def test_the_answer_of_a_clean_repository_is_the_answer_of_git(tmp_path, base):
    """The repository without a change lists nothing, as Git lists nothing."""
    root = shape_repository(tmp_path, base, lambda root: None)
    head = head_of(root)
    assert native.git(root, "diff", "--name-only", "-z", head) == git(root, "diff", "--name-only", "-z", head) == b""


def test_the_diff_of_the_working_tree_starts_no_process(tmp_path, base):
    """The diff is read from the tree, the index and the working tree."""
    root = shape_repository(tmp_path, base, shape_modified)
    head = head_of(root)
    with processes() as started:
        answer = native.git(root, "diff", "--name-only", "-z", head)
    assert answer == git(root, "diff", "--name-only", "-z", head)
    assert len(started) <= DIFF_BUDGET


def test_the_diff_between_two_revisions_starts_no_process(tmp_path, base):
    """The delta between two revisions is read from the two trees."""
    root = shape_repository(tmp_path, base, shape_second_commit)
    head = head_of(root)
    base_sha = git(root, "rev-list", "--max-parents=0", "HEAD").decode().strip()
    with processes() as started:
        answer = native.git(root, "diff", "-z", base_sha, "HEAD", "--name-only")
    assert answer == git(root, "diff", "-z", base_sha, "HEAD", "--name-only")
    assert len(started) <= DIFF_BUDGET


def test_the_diff_of_the_index_starts_no_process(tmp_path, base):
    """The delta between the working tree and the index is read from both."""
    root = shape_repository(tmp_path, base, shape_modified)
    with processes() as started:
        answer = native.git(root, "diff", "-z", "--name-only")
    assert answer == git(root, "diff", "-z", "--name-only")
    assert len(started) <= DIFF_BUDGET


def test_the_delta_of_the_index_starts_no_process(tmp_path, base):
    """The delta between the index and a revision is read from both."""
    root = shape_repository(tmp_path, base, shape_added_in_the_index)
    head = head_of(root)
    with processes() as started:
        answer = native.git(root, "diff", "-z", "--cached", "--name-only")
    assert answer == git(root, "diff", "-z", "--cached", "--name-only")
    assert len(started) <= DIFF_BUDGET


def test_a_stale_read_is_never_served(tmp_path, base):
    """The answer of the diff is the state of the working tree now.

    A file that changed, appeared or vanished is in the answer at once: the
    answer is read from the working tree, and it is not a value kept from
    an earlier moment.
    """
    root = shape_repository(tmp_path, base, lambda root: None)
    head = head_of(root)
    assert native.git(root, "diff", "--name-only", "-z", head) == b""
    write(root, "page.html", "<main>two</main>")
    assert native.git(root, "diff", "--name-only", "-z", head) == b"page.html\0"
    write(root, "late.html", "<main>late</main>")
    git(root, "add", "late.html")
    assert native.git(root, "diff", "--name-only", "-z", head) == b"late.html\0page.html\0"
    os.remove(Path(root) / "late.html")
    assert native.git(root, "diff", "--name-only", "-z", head) == b"page.html\0"


def test_a_moved_head_is_a_different_answer(tmp_path, base):
    """A revision that moved has its own answer."""
    root = shape_repository(tmp_path, base, lambda root: None)
    old = head_of(root)
    write(root, "second.html", "<main>second</main>")
    commit_all(root, "second")
    new = head_of(root)
    assert native.git(root, "diff", "--name-only", "-z", old) == b"second.html\0"
    assert native.git(root, "diff", "--name-only", "-z", new) == b""


def test_a_shape_git_alone_reads_is_left_to_git(tmp_path, base):
    """A shape the module cannot read byte for byte is answered by Git.

    A rename Git would pair is such a shape: which pair Git picks is Git's
    own decision, so the question stays with Git.
    """
    root = shape_repository(tmp_path, base, shape_renamed_in_the_index)
    head = head_of(root)
    assert native.git(root, "diff", "--name-only", "-z", head) == git(root, "diff", "--name-only", "-z", head)


# ---------------------------------------------------------------------------
# The plan tools
# ---------------------------------------------------------------------------


def leaf(plan_dir, name, label="Задача"):
    leaves = plan_dir / "leaves"
    leaves.mkdir(parents=True, exist_ok=True)
    path = leaves / f"{name}.json"
    path.write_text('{"id": "%s", "label": "%s", "status": "queued"}' % (name, label),
                    encoding="utf-8")
    return path


def test_the_plan_tools_run_in_this_process(tmp_path):
    """The collector and the renderer answer in the process that asks them."""
    plan_dir = tmp_path / "plan"
    path = leaf(plan_dir, "L12")
    event = {"cwd": str(tmp_path), "tool_input": {"file_path": str(path)}}
    with processes() as started:
        rendered = entry.render_written_plan(event, ROOT)
    assert rendered == plan_dir
    assert (plan_dir / "plan.graph.json").is_file()
    assert (plan_dir / "plan.html").is_file()
    assert len(started) <= PLAN_BUDGET


def test_a_broken_leaf_is_named_and_the_build_stops(tmp_path):
    """A leaf that cannot be read is named, never silently dropped."""
    plan_dir = tmp_path / "plan"
    path = leaf(plan_dir, "L12")
    path.write_text("{not json", encoding="utf-8")
    event = {"cwd": str(tmp_path), "tool_input": {"file_path": str(path)}}
    with pytest.raises(entry.PlanBuildError) as error:
        entry.render_written_plan(event, ROOT)
    assert "L12" in str(error.value)


# ---------------------------------------------------------------------------
# The Opencode boundary: the plugin payload and the hook binary
# ---------------------------------------------------------------------------

ENTRY = TOOLS / "lhc_entry.py"
PLUGIN_TS = ROOT / "plugins" / "last-human-commit" / "opencode" / "lhc-v2.ts"


def run_opencode_hook(payload, project):
    """Run the hook binary exactly the way the Opencode plugin spawns it."""
    return subprocess.run(
        [sys.executable, str(ENTRY), "--event", "PostToolUse", "--heartbeat-only",
         "--runtime", "opencode"],
        cwd=str(project), input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, timeout=120)


def test_an_opencode_event_rebuilds_the_plan_of_the_written_leaf(tmp_path):
    """The real consumer path: a payload of the Opencode shape rebuilds the page.

    The hook binary is started the way Opencode starts it, the payload names
    a leaf that has just been written, and the graph and the page of that
    plan appear.  This is the promise the plugin used to break by sending
    only cwd and session_id.
    """
    plan_dir = tmp_path / "task"
    path = leaf(plan_dir, "L14")
    result = run_opencode_hook(
        {"cwd": str(tmp_path), "session_id": "ses_l14",
         "tool_input": {"file_path": str(path)}},
        tmp_path)
    assert result.returncode == 0, result.stderr
    assert "пересобрана" in result.stdout, result.stdout
    assert (plan_dir / "plan.graph.json").is_file()
    assert (plan_dir / "plan.html").is_file()


def test_the_old_opencode_payload_without_tool_input_changes_nothing(tmp_path):
    """A payload of the old shape stays harmless: exit 0, no rebuild, no crash.

    Nothing was ever rebuilt from cwd and session_id alone; the guard still
    answers its heartbeat and never touches the plan of the task.
    """
    plan_dir = tmp_path / "task"
    leaf(plan_dir, "L14")
    result = run_opencode_hook({"cwd": str(tmp_path), "session_id": "ses_l14"}, tmp_path)
    assert result.returncode == 0, result.stderr
    assert (plan_dir / "plan.graph.json").exists() is False
    assert (plan_dir / "plan.html").exists() is False
    assert "пересобрана" not in result.stdout


def test_the_opencode_plugin_puts_the_written_paths_into_the_payload(tmp_path):
    """The plugin must forward the tool arguments of `tool.execute.after`.

    The plugin module is instantiated by Node exactly as OpenCode loads it,
    a tool boundary arrives with the arguments of a write into leaves/, and
    the payload the plugin pipes into the hook must carry them as
    tool_input.  The hook binary is replaced by a recorder so this case
    reads the wire, not the promise.
    """
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to run the OpenCode plugin contract")
    package = tmp_path / "package"
    (package / "tools").mkdir(parents=True)
    (package / "tools" / "lhc_entry.py").write_text("# recorder stand-in\n", encoding="utf8")
    project = tmp_path / "project"
    project.mkdir()
    recorded = tmp_path / "payload.json"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "python3"
    shim.write_text('#!/bin/sh\ncat > "%s"\n' % recorded, encoding="utf8")
    shim.chmod(0o755)
    driver = tmp_path / "drive.mts"
    driver.write_text(
        "import plugin from %s\n"
        "const hooks = await plugin({ directory: %s, worktree: %s })\n"
        "await hooks['tool.execute.after'](\n"
        "  { tool: 'write', sessionID: 'ses_wire', callID: 'call_1',\n"
        "    args: { filePath: '/task/leaves/L14.json', content: '{}' } },\n"
        "  { title: 'write', output: '' })\n"
        % (json.dumps(str(PLUGIN_TS)), json.dumps(str(project)), json.dumps(str(project))),
        encoding="utf8")
    env = dict(os.environ, LHC_PLUGIN_ROOT=str(package),
               PATH="%s:%s" % (bin_dir, os.environ["PATH"]))
    result = subprocess.run([node, "--experimental-strip-types", str(driver)],
                            cwd=str(tmp_path), env=env,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    payload = json.loads(recorded.read_text(encoding="utf8"))
    assert payload["cwd"] == str(project)
    assert payload["session_id"] == "ses_wire"
    assert payload["tool_input"]["filePath"] == "/task/leaves/L14.json"
