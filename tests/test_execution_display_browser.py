"""One isolated Chrome journey through execution evidence, without real sessions."""
import base64
import json
import time
import os
from pathlib import Path
import pytest
from test_plan_dashboard_browser import browser
from test_execution_display import grid, document, leaf, ROOT

pytestmark = pytest.mark.skipif(os.environ.get("LHC_UI_BROWSER_TESTS") != "1", reason="opt-in isolated Chrome")


def test_execution_evidence_opens_on_desktop_and_mobile(browser, tmp_path):
    call, js, url = browser
    graph = grid.parse_graph_json(document([leaf()]))
    (tmp_path / "plan.html").write_text(grid.render_html(graph, grid.build_metrics(graph)))
    call("Page.enable")
    call("Page.navigate", {"url": url})
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if js('!!window.__lhcUI && !!document.querySelector(".leaf-row")'):
            break
        time.sleep(.05)
    else:
        pytest.fail("source-rendered plan did not initialize")
    js('document.querySelector(".leaf-row").click()')
    text = js('document.querySelector(".task-details-row").innerText')
    for expected in ("ACTUAL_ACTOR", "ROOT_LEAD", "NATIVE_PARENT", "CHILD_EXECUTOR", "PLANNED_MODEL", "OBSERVED_MODEL", "WAIT-7", "codex_quota_guard"):
        assert expected in text, expected
    assert js('document.body.innerText.toLocaleLowerCase().includes("кандидаты по зависимостям")'), js('document.body.innerText')[:10000]
    proof = ROOT / ".tmp/worker-run"
    proof.mkdir(parents=True, exist_ok=True)
    js('document.querySelector(".task-details-row").scrollIntoView({block:"start"})')
    (proof / "execution-display-desktop.png").write_bytes(base64.b64decode(call("Page.captureScreenshot", {"format": "png"})["data"]))
    call("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
    assert js('document.documentElement.scrollWidth <= innerWidth + 1')
    assert "CHILD_EXECUTOR" in js('document.querySelector(".task-details-row").innerText')
    (proof / "execution-display-mobile.png").write_bytes(base64.b64decode(call("Page.captureScreenshot", {"format": "png"})["data"]))
