"""Public-safe sample rendered by the real LHC renderer, not a second Gantt UI."""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def build_demo(root: Path, dist: Path) -> dict:
    fixture = root / "site/examples/task-plan.graph.json"
    renderer = root / "src/common/tools/lhc_grid.py"
    out = dist / "examples"
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lhc-public-demo-") as folder:
        graph_path = Path(folder) / "plan.graph.json"
        def run(*args: str) -> None:
            result = subprocess.run([sys.executable, str(renderer), *args], cwd=root, text=True, capture_output=True, timeout=30)
            if result.returncode:
                raise RuntimeError("Demo renderer failed: " + result.stdout + result.stderr)
        # The graph is the single authored fixture; do not infer multiple dependencies from prose.
        graph = json.loads(fixture.read_text(encoding="utf-8"))
        graph["title"] = "Демонстрационный план: от сообщения к задаче"
        graph["current_progress"] = "УЧЕБНЫЙ ПРИМЕР. Все времена, статусы и результаты условные: 4 листа завершены, 3 выполняются, 9 ожидают зависимостей. Это не состояние действующей команды."
        graph["external_waits"] = "Нет подключения к ExManager, Airlock, почте или аккаунтам. Новые статусы появятся только после изменения источника и повторной генерации HTML."
        graph["slots"] = 3
        tasks = graph["tasks"]
        if len(tasks) != 16:
            raise ValueError("The demo must retain all sixteen leaves")
        for task in tasks:
            estimate = task.get("estimate_minutes") or {}
            if not 0 < estimate.get("maximum", 0) <= 15:
                raise ValueError("Demo leaves must be bounded by 15 minutes: " + task["id"])
            task["role"] = "Демонстрационный исполнитель"
            task["owner"] = "Учебная команда"
        graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run("validate", str(graph_path))
        run("render", str(graph_path), "-o", str(out / "task-plan.html"))
        # An inspectable input accompanies the HTML; it contains only our public fixture.
        (out / "task-plan.graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html = (out / "task-plan.html").read_text(encoding="utf-8")
    for forbidden in ("telegram:", "account_id", "account_ref", "/home/", "bezrabotnyi.com", "action_db", "8810909089"):
        if forbidden in html:
            raise ValueError("Private detail in public demo: " + forbidden)
    return {"file": "examples/task-plan.html", "leaves": len(tasks), "slots": graph["slots"], "kind": "illustrative-snapshot", "source": "site/examples/task-plan.graph.json", "renderer": "src/common/tools/lhc_grid.py"}
