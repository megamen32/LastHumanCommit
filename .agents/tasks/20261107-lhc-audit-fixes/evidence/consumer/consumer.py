#!/usr/bin/env python3
"""Independent consumer of an isolated native LHC package. Never imports product code."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import sys
import time
import uuid

BASE = Path(__file__).resolve().parent
class ConsumerFailure(RuntimeError):
    pass

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def texts(value):
    found = []
    def visit(item):
        if isinstance(item, dict):
            for key, val in item.items():
                if key in ("text", "stdout", "stderr") and isinstance(val, str):
                    try:
                        decoded = json.loads(val)
                    except (ValueError, TypeError):
                        found.append(val)
                    else:
                        if isinstance(decoded, (dict, list)):
                            visit(decoded)
                        else:
                            found.append(val)
                elif isinstance(val, (dict, list)):
                    visit(val)
        elif isinstance(item, list):
            for val in item:
                visit(val)
    visit(value)
    return "\n".join(found)

def decoded_objects(value):
    found = []
    def visit(item):
        if isinstance(item, dict):
            found.append(item)
            for val in item.values():
                visit(val)
        elif isinstance(item, list):
            for val in item:
                visit(val)
        elif isinstance(item, str):
            try:
                val = json.loads(item)
            except (ValueError, TypeError):
                return
            if isinstance(val, (dict, list)):
                visit(val)
    visit(value)
    return found

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

class Client:
    def __init__(self, runner, cwd):
        self.r = runner
        self.seq = 0
        self.buffer = b""
        self.pending = []
        self.stderr = b""
        self.p = subprocess.Popen(
            ["python3", str(runner.package / "scripts/plan_mcp.py")],
            cwd=cwd, env=runner.env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.sel = selectors.DefaultSelector()
        self.sel.register(self.p.stdout, selectors.EVENT_READ, "stdout")
        self.sel.register(self.p.stderr, selectors.EVENT_READ, "stderr")
        init = self.request("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "lhc-independent-consumer", "version": "1"}})
        version = init.get("result", {}).get("serverInfo", {}).get("version")
        runner.require(version == runner.expected, "MCP server version matches copied manifest",
                       {"reported": version, "expected": runner.expected})
        self.p.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        self.p.stdin.flush()

    def request(self, method, params):
        self.seq += 1
        identifier = self.seq
        call_id = self.r.next_id(method.replace("/", "_"))
        request = {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params}
        write_json(self.r.run / "calls" / (call_id + "-intent.json"),
                   {"pid": self.p.pid, "request": request})
        self.p.stdin.write((json.dumps(request) + "\n").encode())
        self.p.stdin.flush()
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            for n, item in enumerate(self.pending):
                if item.get("id") == identifier:
                    response = self.pending.pop(n)
                    write_json(self.r.run / "calls" / (call_id + "-response.json"), response)
                    return response
            for key, _ in self.sel.select(0.25):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    self.sel.unregister(key.fileobj)
                    continue
                if key.data == "stderr":
                    self.stderr += chunk
                    continue
                self.buffer += chunk
                while b"\n" in self.buffer:
                    line, self.buffer = self.buffer.split(b"\n", 1)
                    if line:
                        self.pending.append(json.loads(line))
            if self.p.poll() is not None and not self.sel.get_map():
                break
        raise ConsumerFailure("MCP request outcome unavailable; inspect intent before any retry: " + call_id)

    def close(self):
        if not self.p.stdin.closed:
            self.p.stdin.close()
        if self.p.poll() is None:
            self.p.terminate()
        try:
            self.p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait(timeout=3)
        self.sel.close()
        if self.stderr:
            (self.r.run / "mcp-stderr.txt").open("ab").write(self.stderr)

class Runner:
    def __init__(self, source, expected):
        self.expected = expected
        self.number = 0
        self.results = []
        self.run = BASE / "runs" / (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8])
        self.run.mkdir(parents=True)
        self.package = self.run / "package"
        shutil.copytree(source, self.package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.fixture_root = self.run / "fixtures"
        self.fixture_root.mkdir()
        self.env = dict(os.environ)
        self.original_home = self.env.get("HOME")
        self.original_codex_home = self.env.get("CODEX_HOME")
        for key in ("CODEX_THREAD_ID", "CLAUDE_SESSION_ID", "CLAUDE_PROJECT_DIR",
                    "ZCODE_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT", "CODEX_PLUGIN_ROOT", "PLUGIN_ROOT"):
            self.env.pop(key, None)
        for key, sub in {"XDG_STATE_HOME": "state", "XDG_CONFIG_HOME": "config",
                         "XDG_CACHE_HOME": "cache", "XDG_DATA_HOME": "data",
                         "TMPDIR": "tmp"}.items():
            target = self.run / sub
            target.mkdir()
            self.env[key] = str(target)
        self.env["LHC_PLAN_MIRROR_CONFIG"] = str(self.run / "config" / "mirror-not-configured.json")
        self.env["LHC_CATALOG_FILE"] = str(self.run / "config" / "catalog-not-configured.json")
        self.env["LHC_MODELS_CACHE_DIR"] = str(self.run / "cache" / "models")
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.env["CODEX_PLUGIN_ROOT"] = str(self.package)
        self.env["LHC_LINK_WAIT_SECONDS"] = "0"
        manifest = json.loads((self.package / ".codex-plugin/plugin.json").read_text())
        write_json(self.run / "run.json", {
            "pid": os.getpid(), "source": str(source), "package": str(self.package),
            "expected_version": expected, "manifest": manifest, "scope": "synthetic isolated consumer fixtures",
            "home_unchanged": self.env.get("HOME") == self.original_home,
            "codex_home_unchanged": self.env.get("CODEX_HOME") == self.original_codex_home,
            "model_sessions_created": 0, "live_installations": 0,
            "copied_hashes": {p: digest(self.package / p) for p in (
                ".codex-plugin/plugin.json", "scripts/plan_mcp.py", "tools/lhc_plan_json.py",
                "tools/lhc_entry.py", "tools/lhc_plan_mcp.py", "com.openai/hooks/hooks.json")}})
        (BASE / "latest-run.txt").write_text(str(self.run) + "\n")
        self.require(manifest["version"] == expected, "copied native package has expected version", manifest["version"])

    def next_id(self, name):
        self.number += 1
        return f"{self.number:04d}-{name}"

    def save(self):
        write_json(self.run / "summary.json", {"checks": self.results,
            "passed": sum(x["ok"] for x in self.results), "failed": sum(not x["ok"] for x in self.results),
            "package": str(self.package), "run": str(self.run)})

    def require(self, condition, title, observation=None):
        self.results.append({"ok": bool(condition), "check": title, "observation": observation})
        self.save()
        if not condition:
            raise ConsumerFailure(title + ": " + json.dumps(observation, ensure_ascii=False)[:1800])

    def cli(self, argv, cwd, *, data=None, expected_error=False):
        call_id = self.next_id("cli")
        write_json(self.run / "calls" / (call_id + "-intent.json"), {"argv": argv, "cwd": str(cwd), "stdin": data})
        try:
            p = subprocess.run(argv, cwd=cwd, env=self.env, input=data, text=True,
                               capture_output=True, timeout=40)
        except subprocess.TimeoutExpired as exc:
            write_json(self.run / "calls" / (call_id + "-timeout.json"), {"timeout": 40})
            raise ConsumerFailure("CLI timed out, do not replay without inspecting artifacts: " + call_id) from exc
        result = {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
        write_json(self.run / "calls" / (call_id + "-response.json"), result)
        self.require((p.returncode != 0) == expected_error, "CLI expected exit: " + " ".join(argv[:3]), result)
        return result

    def tool(self, name, args, *, expected_error=False):
        client = Client(self, self.fixture_root)
        try:
            response = client.request("tools/call", {"name": name, "arguments": args})
        finally:
            client.close()
        error = bool(response.get("error") or response.get("result", {}).get("isError"))
        self.require(error == expected_error, "MCP " + name + " expected outcome", response if error != expected_error else {"isError": error})
        return response

    def project(self, name):
        path = self.fixture_root / name
        path.mkdir()
        self.cli(["git", "init", "--quiet", str(path)], self.fixture_root)
        (path / "fixture-source.txt").write_text("Synthetic consumer fixture; no user work, no release.\n")
        return path

    def fields(self, goal, *, decomposition="complete", cap=60):
        fields = {
            "title": "Independent consumer fixture", "goal": goal, "mode": "fullcycle",
            "deliverable": "plan", "decomposition": decomposition,
            "default_model": "gpt-6-luna", "slots": 2,
            "recon": [
                "The independent consumer file exists before any fixture operation :: " + str(BASE / "consumer.py"),
                "The isolated run record identifies the exact copied package and its version :: " + str(self.run / "run.json"),
                "The disposable fixture directory exists separately from all product source files :: " + str(self.fixture_root)],
            "acceptance_scenario": "Run this synthetic consumer through public MCP and hook commands.",
            "current_progress": "Fixture prepared for independent package acceptance."}
        if cap is not None:
            fields["estimate_policy"] = {"leaf_cap_minutes": cap,
                "reason": "Owner explicitly requested leaves up to 60 minutes"}
        return fields

    def plan(self, project, name, fields):
        path = project / ".agents/tasks" / name
        self.tool("update_plan", {"plan_dir": str(path), "fields": fields})
        return path

    def leaf(self, plan, identifier, *, parent="M01", minutes=5, status="queued", **extra):
        value = {"id": identifier, "label": "Consumer fixture " + identifier,
                 "description": "Synthetic independent consumer work for " + identifier,
                 "acceptance": "The public consumer observes the expected result for " + identifier,
                 "status": status, "estimate_minutes": minutes}
        if parent:
            value["parent"] = parent
        value.update(extra)
        return self.tool("create_leaf", {"plan_dir": str(plan), "leaf": value})

    def milestone(self, plan, identifier):
        return self.tool("create_leaf", {"plan_dir": str(plan), "leaf": {
            "id": identifier, "kind": "milestone", "label": "Fixture milestone " + identifier,
            "status": "queued", "description": "Consumer-visible stage", "acceptance": "Its leaves are testable"}})

    def canonical(self, command, plan, *flags, expected_error=False):
        return self.cli(["python3", str(self.package / "tools/lhc_plan_json.py"),
                         command, str(plan), *flags], plan.parent, expected_error=expected_error)

    def source_snapshot(self, plan):
        return {str(p.relative_to(plan)): digest(p) for p in [plan / "plan.json", *sorted((plan / "leaves").glob("*.json"))]}

    def hook(self, event, cwd, session):
        manifest = json.loads((self.package / "com.openai/hooks/hooks.json").read_text())
        handlers = [h for group in manifest["hooks"][event] for h in group["hooks"]
                    if "--instructions-only" in h["command"]]
        self.require(len(handlers) == 1, "one actual native instructions hook selected", event)
        response = self.cli(["bash", "-c", handlers[0]["command"]], cwd,
                            data=json.dumps({"cwd": str(cwd), "session_id": session}))
        try:
            payload = json.loads(response["stdout"])
        except ValueError as exc:
            raise ConsumerFailure("Hook did not emit its consumer JSON: " + event) from exc
        context = payload.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.require(bool(context), "hook emits additionalContext", event)
        (self.run / (self.next_id(event) + "-context.txt")).write_text(context)
        return context

    def run_cases(self):
        client = Client(self, self.fixture_root)
        try:
            listed = client.request("tools/list", {})
        finally:
            client.close()
        tools = {t["name"]: t for t in listed.get("result", {}).get("tools", [])}
        self.require("handoff" in tools["build_plan"]["inputSchema"]["properties"],
                     "published MCP schema exposes handoff", tools["build_plan"]["inputSchema"])

        project = self.project("policy-project")
        plan = self.plan(project, "policy60", self.fields("POLICY60_CONSUMER_GOAL"))
        self.milestone(plan, "M01")
        self.leaf(plan, "L01", status="done", result="Synthetic fixture construction is complete.")
        self.leaf(plan, "L02", minutes=60)
        self.tool("update_leaf", {"plan_dir": str(plan), "leaf_id": "L02", "fields": {"estimate_minutes": 45}})
        # Each call creates a fresh MCP process; persistence is exercised at every boundary.
        self.tool("update_leaf", {"plan_dir": str(plan), "leaf_id": "L02", "fields": {"estimate_minutes": 60}})
        persisted = json.loads((plan / "plan.json").read_text())["estimate_policy"]
        self.require(persisted["leaf_cap_minutes"] == 60, "explicit cap survives process restart", persisted)
        self.tool("build_plan", {"plan_dir": str(plan), "handoff": True})
        self.canonical("check", plan, "--handoff")
        graph = json.loads((plan / "plan.graph.json").read_text())
        policies = [o["estimate_policy"] for o in decoded_objects(graph) if isinstance(o.get("estimate_policy"), dict)]
        self.require(any(p.get("leaf_cap_minutes") == 60 for p in policies), "graph exports policy60", policies)
        rendered = VisibleText()
        rendered.feed((plan / "plan.html").read_text())
        visible = " ".join(rendered.parts)
        stale_warning = re.findall(r"(?:over|exceed|more than|больше|превышает|длиннее)[^.\n]{0,100}15\s*(?:min|мин)", visible, re.I)
        self.require(not stale_warning, "UI has no obsolete 15-minute over-limit warning", stale_warning)
        self.tool("update_leaf", {"plan_dir": str(plan), "leaf_id": "L02", "fields": {"estimate_minutes": 61}}, expected_error=True)
        self.require(json.loads((plan / "leaves/L02.json").read_text())["estimate_minutes"] == 60,
                     "over-cap update is atomic")
        self.tool("create_leaf", {"plan_dir": str(plan), "leaf": {
            "id": "L03", "label": "Over cap", "parent": "M01", "estimate_minutes": 61,
            "description": "Invalid synthetic task", "acceptance": "Must be refused"}}, expected_error=True)
        self.require(not (plan / "leaves/L03.json").exists(), "over-cap create leaves no invalid file")

        shown = self.tool("show_plan", {"plan_dir": str(plan), "current": ["L01"]})
        (self.run / "show-plan-current-done.txt").write_text(texts(shown))
        objects = decoded_objects(shown)
        summary_objects = [o for o in objects if "now" in o and "done" in o]
        if summary_objects:
            summary = summary_objects[0]
            self.require("L01" not in json.dumps(summary["now"]), "done L01 excluded from Now", summary)
        else:
            output = texts(shown)
            match = re.search(r"(?ims)^\s*(?:#+\s*)?Now\s*:?\s*$([\s\S]*?)(?=^\s*(?:#+\s*)?(?:Done|Next|Elsewhere|Overruns|Blocked|Workers|Waiting)\b|\Z)", output)
            done = re.search(r"(?ims)^\s*Done\s*:\s*$([\s\S]*?)(?=^\s*(?:Now|Next|Elsewhere|Overruns|Blocked|Workers|Waiting)\b|\Z)", output)
            self.require(bool(done and "L01" in done.group(1)), "show_plan explicitly confirms L01 under Done", output)
            if match:
                now_text = match.group(1)
            else:
                self.require(not re.search(r"(?im)^\s*(?:#+\s*)?Now\b", output),
                             "empty Now is omitted rather than unreadable", output)
                now_text = ""
            self.require("L01" not in now_text, "done L01 excluded from Now", now_text)

        self.milestone(plan, "M02")
        incomplete = self.tool("build_plan", {"plan_dir": str(plan), "handoff": True}, expected_error=True)
        self.require("M02" in texts(incomplete), "complete handoff names the empty milestone", texts(incomplete))
        self.canonical("check", plan, "--handoff", expected_error=True)
        self.tool("update_plan", {"plan_dir": str(plan), "fields": {"decomposition": "progressive"}})
        progressive = self.tool("build_plan", {"plan_dir": str(plan), "handoff": True})
        graph = json.loads((plan / "plan.graph.json").read_text())
        report = (plan / "plan.md").read_text()
        self.require(any(o.get("decomposition") == "progressive" for o in decoded_objects(graph)),
                     "graph preserves progressive decomposition")
        self.require(bool(re.search(r"progressive|partial|частич|поэтап", report + "\n" + texts(progressive), re.I)),
                     "progressive handoff explicitly reports partial decomposition", report[:3000])

        hook_project = self.project("bound-project")
        unrelated_project = self.project("other-cwd")
        hook_plan = self.plan(hook_project, "explicit-binding", self.fields("OLD_GOAL_CONSUMER_MARKER", decomposition="progressive", cap=30))
        self.milestone(hook_plan, "M01")
        # Bulk fixture data is synthetic input, never a product source or worker regression.
        for i in range(1, 421):
            leaf = {"id": f"L{i:03d}", "label": f"Fixture leaf {i}", "parent": "M01",
                    "description": "Synthetic historical fixture", "acceptance": "Fixture exists",
                    "status": "queued", "estimate_minutes": 1}
            write_json(hook_plan / "leaves" / (leaf["id"] + ".json"), leaf)
        self.leaf(hook_plan, "L450", minutes=1)
        self.leaf(hook_plan, "L451", minutes=1)
        session = "audit-consumer-" + uuid.uuid4().hex
        for leaf_id in ("L450", "L451"):
            self.tool("activate_leaf", {"plan_dir": str(hook_plan), "leaf_id": leaf_id,
                       "session": session, "harness": "codex", "note": "Synthetic consumer explicit binding"})
        decoy = self.plan(unrelated_project, "cwd-only-decoy", self.fields("DECOY_GOAL_MUST_NOT_RESUME", decomposition="progressive"))
        self.milestone(decoy, "M01")
        self.leaf(decoy, "L01", minutes=1)
        before = self.source_snapshot(hook_plan)
        start = self.hook("SessionStart", unrelated_project, session)
        self.require("OLD_GOAL_CONSUMER_MARKER" in start, "SessionStart restores explicitly bound goal across cwd and >400 leaves")
        self.require("DECOY_GOAL_MUST_NOT_RESUME" not in start, "SessionStart does not adopt cwd-only plan")
        self.require(self.source_snapshot(hook_plan) == before, "SessionStart does not alter plan or leaf state")

        self.tool("update_plan", {"plan_dir": str(hook_plan), "fields": {
            "goal": "FRESH_GOAL_CONSUMER_MARKER",
            "current_progress": "FRESH_PROGRESS_CONSUMER_MARKER",
            "estimate_policy": {"leaf_cap_minutes": 60, "reason": "FRESH_POLICY_CONSUMER_MARKER"}},
            "revision": {"reason": "Synthetic owner scope update", "summary": "FRESH_REVISION_CONSUMER_MARKER"}})
        before = self.source_snapshot(hook_plan)
        compact = self.hook("PostCompact", unrelated_project, session)
        for token in ("FRESH_GOAL_CONSUMER_MARKER", "FRESH_PROGRESS_CONSUMER_MARKER", "FRESH_REVISION_CONSUMER_MARKER"):
            self.require(token in compact, "PostCompact restores current fact " + token)
        self.require("60" in compact and ("estimate_policy" in compact or re.search(r"policy|политик|лимит|cap", compact, re.I)),
                     "PostCompact restores fresh cap60 policy")
        self.require("OLD_GOAL_CONSUMER_MARKER" not in compact and "DECOY_GOAL_MUST_NOT_RESUME" not in compact,
                     "PostCompact avoids obsolete goal and cwd-only goal")
        self.require(self.source_snapshot(hook_plan) == before, "PostCompact does not alter plan or leaf state")
        unknown = self.hook("PostCompact", unrelated_project, "unbound-" + uuid.uuid4().hex)
        self.require("FRESH_GOAL_CONSUMER_MARKER" not in unknown and "DECOY_GOAL_MUST_NOT_RESUME" not in unknown,
                     "unbound session does not resume by cwd")

        missing = self.canonical("activate", hook_plan, "L001", "--harness", "codex", expected_error=True)
        error_text = missing["stdout"] + "\n" + missing["stderr"]
        self.require("Traceback" not in error_text and bool(re.search(r"--session|CODEX_THREAD_ID|session id|session identity", error_text, re.I)),
                     "missing-session CLI activation is readable and actionable", error_text)
        missing_mcp = self.tool("activate_leaf", {"plan_dir": str(hook_plan), "leaf_id": "L001", "harness": "codex"}, expected_error=True)
        error_text = texts(missing_mcp)
        self.require("Traceback" not in error_text and bool(re.search(r"--session|CODEX_THREAD_ID|session id|session identity", error_text, re.I)),
                     "missing-session MCP activation is readable and actionable", error_text)
        self.require(json.loads((hook_plan / "leaves/L001.json").read_text())["status"] == "queued",
                     "failed activation preserves the queued leaf")
        self.require(not Path(self.env["LHC_PLAN_MIRROR_CONFIG"]).exists(), "no mirror configuration or publication enabled")
        self.require(self.env.get("HOME") == self.original_home and self.env.get("CODEX_HOME") == self.original_codex_home,
                     "HOME and CODEX_HOME were preserved")
        write_json(self.run / "complete.json", {"ok": True, "at": datetime.now(timezone.utc).isoformat()})
        self.save()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-package", type=Path, required=True)
    parser.add_argument("--expected-version", default="1.16.1")
    args = parser.parse_args()
    runner = Runner(args.source_package.resolve(), args.expected_version)
    print(json.dumps({"started": str(runner.run), "pid": os.getpid()}), flush=True)
    try:
        runner.run_cases()
    except Exception as exc:
        write_json(runner.run / "failure.json", {"type": type(exc).__name__, "message": str(exc)})
        print(json.dumps({"ok": False, "run": str(runner.run), "error": str(exc)}, ensure_ascii=False), flush=True)
        return 1
    print(json.dumps({"ok": True, "run": str(runner.run), "package": str(runner.package),
                      "checks": len(runner.results)}, ensure_ascii=False), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
