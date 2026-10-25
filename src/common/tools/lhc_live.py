#!/usr/bin/env python3
"""The page that keeps itself in sync with the file it was built from.

The dashboard is rendered in Python and stays that way: the page never renders
a plan in JavaScript. What this module adds is a small poller. Every couple of
seconds it asks the server for the very same ``plan.html`` and, when the
content differs from what is on the screen, swaps the content in without a
reload. The plan that changed a second ago is visible without asking anyone
to reload the page.

The swap replaces the body with the body of the freshly rendered file and runs
the file's own scripts again, so the buttons of the new content work as they
did in the file. The poller itself is never restarted by that: it is marked,
and the page refuses to start a second poller.

The poller fetches the page over HTTP. A page opened straight from the disk
(``file://``) is not allowed to fetch itself by the browser, so it stays as it
was rendered - the content is still correct, only the automatic refresh is
unavailable. Serve the plan directory over HTTP to get the live page.

Usage::

    python3 -c "import lhc_live; print(lhc_live.live_snippet())"
"""

from __future__ import annotations

import json
from typing import Optional

LIVE_SCRIPT_ID = "lhc-live"
# The marker that tells the swap not to run the poller again.
LIVE_MARKER = "data-lhc-live"
DEFAULT_INTERVAL_MS = 2000


_SCRIPT_TEMPLATE = """
(function () {
  if (window.__lhcLive) { return; }
  window.__lhcLive = true;
  var source = __LHC_URL__;
  var interval = __LHC_INTERVAL__;

  function address() {
    var base = source || (window.location.href.split('#')[0]);
    if (!base) { return ''; }
    return base + (base.indexOf('?') >= 0 ? '&' : '?') + 'lhc_live=' + Date.now();
  }

  function text_of(node) {
    if (!node) { return ''; }
    var text = node.textContent || '';
    return text.replace(/\\s+/g, ' ').trim();
  }

  function swap(parsed) {
    if (!parsed || !parsed.body) { return false; }
    var body = document.body;
    window.dispatchEvent(new Event('lhc-before-swap'));
    // Inline presentation belongs to the same generation as the new body.
    Array.prototype.slice.call(document.head.querySelectorAll('style')).forEach(function (style) { style.remove(); });
    Array.prototype.slice.call(parsed.head.querySelectorAll('style')).forEach(function (style) { document.head.appendChild(document.importNode(style, true)); });
    var scripts = [];
    Array.prototype.slice.call(parsed.body.querySelectorAll('script')).forEach(
      function (old) { scripts.push(old); }
    );
    while (body.firstChild) { body.removeChild(body.firstChild); }
    while (parsed.body.firstChild) { body.appendChild(document.adoptNode(parsed.body.firstChild)); }
    if (parsed.title) { document.title = parsed.title; }
    scripts.forEach(function (old) {
      if (old.getAttribute('__LHC_MARKER__') === '1') { return; }
      var fresh = document.createElement('script');
      if (old.src) { fresh.src = old.src; } else { fresh.textContent = old.textContent; }
      body.appendChild(fresh);
    });
    return true;
  }

  function poll() {
    var url = address();
    if (!url || typeof window.fetch !== 'function' || typeof window.DOMParser !== 'function') { return; }
    window.fetch(url, { cache: 'no-store', credentials: 'same-origin' })
      .then(function (response) { return response && response.ok ? response.text() : null; })
      .then(function (text) {
        if (!text) { return; }
        var parsed = new DOMParser().parseFromString(text, 'text/html');
        if (!parsed || !parsed.body) { return; }
        if (text_of(parsed.body) === text_of(document.body)) { return; }
        swap(parsed);
      })
      .catch(function () {
        /* A page opened from the disk cannot fetch itself: it stays as rendered. */
      });
  }

  window.setInterval(poll, interval);
  poll();
})();
"""


def live_script(*, url: str = "", interval_ms: int = DEFAULT_INTERVAL_MS) -> str:
    """The JavaScript that polls the page's own file.

    ``url`` is the address of the page to poll. An empty url means the page
    polls itself, which is what a page opened from a plan directory wants.
    """

    source = json.dumps(url or "", ensure_ascii=False)
    interval = max(500, int(interval_ms))
    return (
        _SCRIPT_TEMPLATE
        .replace("__LHC_URL__", source)
        .replace("__LHC_INTERVAL__", str(interval))
        .replace("__LHC_MARKER__", LIVE_MARKER)
        .strip()
    )


def live_snippet(*, url: str = "", interval_ms: int = DEFAULT_INTERVAL_MS) -> str:
    """The script block that belongs into the built page."""

    return (
        f'<script id="{LIVE_SCRIPT_ID}" {LIVE_MARKER}="1">\n'
        f"{live_script(url=url, interval_ms=interval_ms)}\n"
        f"</script>"
    )


def inject_live(
    html: str,
    *,
    url: str = "",
    interval_ms: int = DEFAULT_INTERVAL_MS,
) -> str:
    """Put the live snippet into a built page, once.

    The snippet goes right before the closing body tag, so the page's own
    scripts have already run and the poller starts on a ready page. A page
    that already carries the snippet is returned unchanged: the builder may be
    called again on the same page.
    """

    text = html or ""
    if LIVE_MARKER in text:
        return text
    snippet = live_snippet(url=url, interval_ms=interval_ms)
    closing = text.rfind("</body>")
    if closing < 0:
        return text + snippet
    return text[:closing] + snippet + "\n" + text[closing:]


def plan_url(path: Optional[str] = None) -> str:
    """The address the page of one plan polls.

    A plan directory served over HTTP exposes its page as ``plan.html``; the
    page polls itself, so the address stays empty unless a caller knows
    better.
    """

    if not path:
        return ""
    name = str(path).rsplit("/", 1)[-1]
    return name if name.endswith(".html") else ""
