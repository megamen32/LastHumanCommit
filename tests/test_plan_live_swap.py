"""An unchanged page must not swap its own body.

The local poller compares the text of the fetched page with the text of the open one, but
the open page is already changed by its own scripts, so the two never matched: the whole
body was replaced every 2 s, the sidebar lost its current section and the scroll jumped
(seen as flaky browser tests under load).
"""
import time

from test_plan_dashboard_browser import browser, grid  # noqa: F401  (fixture and renderer)


def test_an_unchanged_page_is_not_swapped(browser, tmp_path):  # noqa: F811
    call, js, url = browser
    doc = {'schema_version': 2, 'title': 'Неизменный план', 'slots': 2,
           'tasks': [{'id': f'L{i:02}', 'label': f'Работа {i}', 'status': 'running' if i == 1 else 'queued',
                      'estimate_minutes': 10, 'note': 'Примечание ' * 120} for i in range(12)]}
    graph = grid.parse_graph_json(doc)
    (tmp_path / 'plan.html').write_text(grid.render_html(graph, grid.build_metrics(graph)))
    call('Page.enable')
    call('Page.navigate', {'url': url})
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not js('!!window.__lhcUI'):
        time.sleep(.05)
    js("window.__swaps=0; window.addEventListener('lhc-before-swap',()=>window.__swaps++)")
    time.sleep(7)  # three polls at 2 s
    assert js('window.__swaps') == 0
