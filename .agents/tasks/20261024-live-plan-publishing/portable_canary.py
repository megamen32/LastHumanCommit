#!/usr/bin/env python3
"""Disposable installed-package consumer. All plan facts here are synthetic."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

package = Path(sys.argv[1]).resolve()
tools = package / "common/tools"


def cli(script, *args):
    completed = subprocess.run([sys.executable, str(tools / script), *map(str, args)], capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(completed.stderr)
    return completed.stdout


def fetch(url):
    with urllib.request.urlopen(url, timeout=15) as response:
        return response.read()


with tempfile.TemporaryDirectory(prefix="lhc-portable-") as temporary:
    plan = Path(temporary) / "lhc-portable-canary"
    plan.mkdir()
    (plan / "plan.json").write_text(json.dumps({"title": "СИНТЕТИЧЕСКАЯ ПРОВЕРКА SSH — не реальная работа", "goal": "Проверка CLI из переносимого пакета через существующий SSH. Все минуты искусственные.", "slots": 1}, ensure_ascii=False))
    cli("lhc_plan_json.py", "create-leaf", plan, "C01", "--fields", json.dumps({"label": "Искусственный контрольный лист", "estimate_minutes": 2}))
    first = json.loads(cli("lhc_plan_publish.py", "publish-html", plan, "--autopublish"))
    url = first["url"]
    original = fetch(url + "r001.html")
    cli("lhc_plan_json.py", "progress", plan, "C01", "--note", "Синтетические факты для проверки; это не измеренное время агента.", "--fields", '{"status":"done","actual_minutes":3}')
    assert original == fetch(url + "r001.html")
    cli("lhc_plan_json.py", "create-leaf", plan, "C02", "--fields", '{"label":"Синтетическая новая работа для r002","estimate_minutes":1,"depends_on":["C01"]}')
    cli("lhc_plan_publish.py", "revise", plan, "--reason", "Синтетический контроль добавления листа; не реальное перепланирование")
    assert original == fetch(url + "r001.html")
    assert "C02" in fetch(url + "r002.html").decode()
    requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize"}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "publish_html", "arguments": {"plan_dir": str(plan)}}}]
    stdio = subprocess.run([sys.executable, str(package / "scripts/plan_mcp.py")], input="\n".join(map(json.dumps, requests)) + "\n", text=True, capture_output=True, check=True)
    replies = [json.loads(line) for line in stdio.stdout.splitlines()]
    assert len(replies) == 3 and not replies[-1]["result"]["isError"]
    parity = json.loads(replies[-1]["result"]["structuredContent"]["stdout"])
    native = json.loads(cli("lhc_plan_publish.py", "publish-html", plan))
    assert parity == native
    print(json.dumps({"url": url, "r001_sha256": hashlib.sha256(original).hexdigest(), "r001_unchanged_after_r002": True, "portable_stdio_initialize_list_call": True, "cli_mcp_parity": True, "source_checkout_dependency": False}, ensure_ascii=False))
