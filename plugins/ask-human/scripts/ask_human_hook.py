#!/usr/bin/env python3
"""Ask Human hook: hand the harness's own question to the human, and return the answer.

The harness already knows how to ask a human. This hook intercepts that exact
moment (the ``PermissionRequest`` hook event), forwards the question through the
Notice Place human-request intake that the AskHuman MCP already uses, waits for
the answer, and gives the answer back to the harness on stdout.

Transport: the HTTP contract of ``ask_human`` in the notify MCP, unchanged.
``POST /v1/human-requests`` with a Bearer token and the ``ask_human.request.v1``
envelope, then ``GET /v1/human-requests/{request_id}`` until the state leaves
``pending``. No second transport is invented here, and no credential is written
to the repository: the address and the token come from the host environment.

The hook never leaves the harness without an answer of some kind. Every path,
including a broken configuration or an unreachable service, ends in an explicit
message on stdout, so the harness still asks the human in its own UI instead of
waiting on a silent hook.

Usage:
    ask_human_hook.py                      # reads the hook payload on stdin
    ask_human_hook.py --event PermissionRequest --timeout 90

Environment:
    ASK_HUMAN_URL                 human-request intake URL
    NOTIFY_CENTER_EVENT_URL       events URL; /events is rewritten to /human-requests
    NOTIFY_CENTER_TOKEN           Bearer token of the producer
    NOTIFY_CENTER_PROJECT         project scope of the question
    NOTIFY_CENTER_RECIPIENT       recipient of the question
    ASK_HUMAN_ALLOWED_ACTORS      actors allowed to answer
    ASK_HUMAN_ENV_FILE            protected env file (default ~/.config/ask-human/env)
    ASK_HUMAN_HOOK_TIMEOUT        seconds to wait for the answer (default 90)
    ASK_HUMAN_DENY_WORDS          words that turn an answer into a refusal
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

#: The keys that carry the human-request intake URL, in the order of preference.
URL_KEYS = ("ASK_HUMAN_URL", "NOTIFY_CENTER_HUMAN_REQUEST_URL", "NOTIFY_CENTER_EVENT_URL")
#: The keys that carry the Bearer token of the producer.
TOKEN_KEYS = ("NOTIFY_CENTER_TOKEN", "ASK_HUMAN_MCP_TOKEN", "LHC_ASKHUMAN_MCP_TOKEN")
#: The keys that carry the project scope.
PROJECT_KEYS = ("NOTIFY_CENTER_PROJECT", "ASK_HUMAN_PROJECT")
#: The keys that carry the recipient.
RECIPIENT_KEYS = ("NOTIFY_CENTER_RECIPIENT",)
#: The keys that carry the actors allowed to answer.
ACTOR_KEYS = ("ASK_HUMAN_ALLOWED_ACTORS",)

#: The protected env file of the host, and the plain dotenv fallbacks.
ENV_FILE = Path("~/.config/ask-human/env")
DOTENV_FILES = (Path(".env"), Path("~/.env"))

DEFAULT_PROJECT = "hermes"
DEFAULT_RECIPIENT = "operator"
DEFAULT_TIMEOUT = 90.0
HTTP_TIMEOUT = 8.0
POLL_INTERVAL = 0.5

#: An answer that contains one of these words is a refusal, not an approval.
DEFAULT_DENY_WORDS = (
    "no", "nope", "deny", "denied", "reject", "rejected", "stop", "abort", "cancel", "halt",
    "нет", "нельзя", "не надо", "отказ", "стоп", "отмена", "запрет", "запретить",
)

#: The tool arguments that carry the actual request, in the order a human reads them.
ARGUMENT_KEYS = (
    "command", "cmd", "script", "file_path", "path", "notebook_path", "url", "query",
    "pattern", "prompt", "message", "description", "content", "input",
)
#: The keys that carry the reason of a question.
REASON_KEYS = ("reason", "justification", "explanation", "why", "message", "prompt", "question")
#: The keys that carry the label and the value of one suggested choice.
CHOICE_LABEL_KEYS = ("label", "title", "text", "name", "mode", "behavior", "destination")
CHOICE_VALUE_KEYS = ("value", "id", "key", "option", "mode", "behavior")


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a KEY=VALUE env file. Values never leave this module."""
    values: dict[str, str] = {}
    try:
        contents = path.expanduser().read_text(encoding="utf-8")
    except OSError:
        return values
    for raw in contents.splitlines():
        line = raw.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def merged_settings(env_file: Path | None = None) -> dict[str, str]:
    """Layer the settings: dotenv, then the protected env file, then the process.

    The process environment wins, because it is the most explicit statement of
    the invocation. The protected env file wins over a plain dotenv, because it
    is the scope the human answers in.
    """
    values: dict[str, str] = {}
    for candidate in DOTENV_FILES:
        values.update(parse_env_file(candidate))
    candidates = (env_file,) if env_file is not None else (ENV_FILE,)
    for candidate in candidates:
        values.update(parse_env_file(candidate))
    values.update(os.environ)
    return values


def first_value(settings: dict[str, str], keys: tuple[str, ...]) -> tuple[str, str]:
    """The first nonempty value of the keys, with the key it came from."""
    for key in keys:
        value = str(settings.get(key) or "").strip()
        if value:
            return value, key
    return "", ""


def human_requests_url(url: str) -> str:
    """The human-request intake URL of a configured events or human-requests URL."""
    base = url.strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/human-requests"):
        return base
    if base.endswith("/events"):
        return base[: -len("/events")] + "/human-requests"
    return base + "/human-requests"


def resolve_settings(env_file: Path | None = None) -> dict[str, object]:
    """The producer identity of this host, read from the host environment."""
    settings = merged_settings(env_file)
    url, url_key = first_value(settings, URL_KEYS)
    token, _ = first_value(settings, TOKEN_KEYS)
    project, _ = first_value(settings, PROJECT_KEYS)
    recipient, _ = first_value(settings, RECIPIENT_KEYS)
    actors_raw, _ = first_value(settings, ACTOR_KEYS)
    actors = [actor.strip() for actor in actors_raw.replace(";", ",").split(",") if actor.strip()]
    timeout_raw = str(settings.get("ASK_HUMAN_HOOK_TIMEOUT") or "").strip()
    try:
        timeout = float(timeout_raw) if timeout_raw else DEFAULT_TIMEOUT
    except ValueError:
        timeout = DEFAULT_TIMEOUT
    deny_raw = str(settings.get("ASK_HUMAN_DENY_WORDS") or "").strip()
    deny_words = tuple(
        word.strip() for word in deny_raw.replace(";", ",").split(",") if word.strip()
    ) if deny_raw else DEFAULT_DENY_WORDS
    return {
        "endpoint": human_requests_url(url),
        "url": url,
        "url_key": url_key,
        "token": token,
        "project": project or DEFAULT_PROJECT,
        "recipient": recipient or DEFAULT_RECIPIENT,
        "actors": actors,
        "timeout": max(timeout, 0.0),
        "deny_words": deny_words,
    }


# ---------------------------------------------------------------------------
# the question
# ---------------------------------------------------------------------------


def clip(text: str, limit: int) -> str:
    """Shorten a text for one message, marking that it was shortened."""
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)] + "..."


def first_string(source: object, keys: tuple[str, ...]) -> str:
    """The first nonempty string of the keys of one mapping."""
    if not isinstance(source, dict):
        return ""
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def summarize_tool_input(tool_input: object, limit: int = 1200) -> str:
    """Render the arguments of the tool call for the human."""
    if tool_input is None:
        return ""
    if not isinstance(tool_input, dict):
        return clip(str(tool_input), limit)
    lines: list[str] = []
    for key in ARGUMENT_KEYS:
        if key not in tool_input:
            continue
        value = tool_input[key]
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        lines.append(f"  {key}: {clip(str(value), limit)}")
        if len(lines) >= 6:
            break
    if not lines:
        lines.append("  " + clip(json.dumps(tool_input, ensure_ascii=False, sort_keys=True), limit))
    return "\n".join(lines)


def extract_choices(suggestions: object) -> list[dict[str, str]]:
    """The offered choices of a question, when there are two to four of them."""
    if not isinstance(suggestions, list):
        return []
    choices: list[dict[str, str]] = []
    for item in suggestions:
        if isinstance(item, str):
            label = item.strip()
            if label:
                choices.append({"label": label, "value": label})
            continue
        if not isinstance(item, dict):
            continue
        label = first_string(item, CHOICE_LABEL_KEYS)
        if not label:
            continue
        value = first_string(item, CHOICE_VALUE_KEYS) or label
        choices.append({"label": label, "value": value})
    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for choice in choices:
        if choice["value"] in seen:
            continue
        seen.add(choice["value"])
        unique.append(choice)
    return unique if 2 <= len(unique) <= 4 else []


def extract_question(payload: dict, event: str) -> dict[str, object]:
    """Read the question the harness asks out of one hook payload."""
    tool_name = first_string(payload, ("tool_name",))
    tool_input = payload.get("tool_input")
    reason = first_string(payload, REASON_KEYS)
    if not reason and isinstance(tool_input, dict):
        reason = first_string(tool_input, REASON_KEYS)
    suggestions = payload.get("permission_suggestions")
    choices = extract_choices(suggestions)

    if event == "Notification":
        text = first_string(payload, ("message", "title"))
        if not text:
            text = "The harness needs your attention."
        return {"text": text, "mode": "question", "choices": [], "tool_name": tool_name,
                "tool_input": tool_input, "reason": ""}

    if event == "Stop":
        text = first_string(payload, ("last_assistant_message", "message"))
        if not text:
            text = ""
        return {"text": text, "mode": "question", "choices": [], "tool_name": tool_name,
                "tool_input": tool_input, "reason": ""}

    # PermissionRequest, and the default: the harness wants a permission.
    parts: list[str] = ["The harness asks for permission before running a tool."]
    if tool_name:
        parts.append(f"\ntool: {tool_name}")
    arguments = summarize_tool_input(tool_input)
    if arguments:
        parts.append("\narguments:\n" + arguments)
    if reason:
        parts.append(f"\nreason: {reason}")
    return {
        # the service keeps the first 4000 characters of a message, so the
        # question is cut here, where the cut is visible
        "text": clip("\n".join(parts), 3800),
        "mode": "choice" if choices else "question",
        "choices": choices,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "reason": reason,
    }


def is_denial(answer: str, deny_words: tuple[str, ...]) -> bool:
    """Whether the answer refuses the request instead of allowing it."""
    words = re.sub(r"[^\w]+", " ", answer.lower())
    normalized = f" {words} "
    for word in deny_words:
        if f" {word.lower()} " in normalized:
            return True
    return False


# ---------------------------------------------------------------------------
# delivery
# ---------------------------------------------------------------------------


def http_json(method: str, url: str, token: str, payload: object | None = None,
              timeout: float = HTTP_TIMEOUT, idempotency_key: str | None = None) -> dict:
    """One authenticated JSON call to the Notice Place API."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read() or b"{}")
        except ValueError:
            body = {}
        raise RuntimeError(str(body.get("error") or body.get("message") or f"HTTP {error.code}")) from error
    except urllib.error.URLError as error:
        raise RuntimeError(str(error.reason)) from error


def build_request(question: dict, settings: dict, request_id: str, expires_at: float) -> dict:
    """The ask_human.request.v1 envelope of one question."""
    payload: dict[str, object] = {
        "schema": "ask_human.request.v1",
        "request_id": request_id,
        "project": settings["project"],
        "recipient": settings["recipient"],
        "mode": question["mode"],
        "message": question["text"],
        "choices": question["choices"] or None,
        "expires_at": expires_at,
    }
    actors = settings["actors"]
    if actors:
        # An empty allowlist is refused by the service; it then derives one of its own.
        payload["allowed_actors"] = actors
    return payload


def poll_answer(endpoint: str, token: str, request_id: str, deadline: float) -> dict:
    """Read the state of the request until it leaves pending or the deadline passes."""
    url = f"{endpoint}/{urllib.parse.quote(request_id, safe='')}"
    body: dict = {}
    while True:
        body = http_json("GET", url, token)
        if str(body.get("state") or "") != "pending":
            return body
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return body
        time.sleep(min(POLL_INTERVAL, remaining))


def run(payload: dict, event: str, settings: dict) -> dict:
    """Ask the human and wait for the answer."""
    question = extract_question(payload, event)
    text = str(question.get("text") or "").strip()
    if not text:
        return {"state": "skipped", "reason": "the hook payload carries no question"}
    endpoint = str(settings["endpoint"])
    token = str(settings["token"])
    if not endpoint:
        return {"state": "failed", "error": f"no human-request URL in {' or '.join(URL_KEYS)}"}
    if not token:
        return {"state": "failed", "error": f"no producer token in {' or '.join(TOKEN_KEYS)}"}

    request_id = f"ask-{uuid.uuid4().hex[:20]}"
    timeout = float(settings["timeout"])
    payload_body = build_request(question, settings, request_id, time.time() + max(timeout + 60, 300))
    http_json("POST", endpoint, token, payload_body, idempotency_key=f"human-request:{request_id}")
    body = poll_answer(endpoint, token, request_id, time.monotonic() + timeout)
    state = str(body.get("state") or "")
    if state == "resolved":
        return {
            "state": "answered",
            "answer": str(body.get("response_value") or "").strip(),
            "actor": str(body.get("response_actor") or "").strip(),
            "request_id": request_id,
        }
    if state == "expired":
        return {"state": "failed", "error": "the question expired before an answer",
                "request_id": request_id}
    return {"state": "pending", "request_id": request_id}


# ---------------------------------------------------------------------------
# the answer back to the harness
# ---------------------------------------------------------------------------


def build_output(event: str, outcome: dict, deny_words: tuple[str, ...]) -> dict:
    """The hook output the harness reads."""
    output: dict[str, object] = {"continue": True}
    state = str(outcome.get("state") or "")
    if state == "answered":
        answer = str(outcome.get("answer") or "").strip()
        output["systemMessage"] = f"Ask Human: {answer}"
        if event == "PermissionRequest":
            behavior = "deny" if is_denial(answer, deny_words) else "allow"
            decision: dict[str, object] = {"behavior": behavior}
            if behavior == "deny":
                # Only the refusal carries a message: the other harnesses read
                # the answer of an approval from the system message, and the
                # reserved fields of the decision fail the hook closed.
                decision["message"] = answer
            output["hookSpecificOutput"] = {
                "hookEventName": "PermissionRequest",
                "decision": decision,
            }
        elif event == "Stop":
            # The Stop hook keeps the turn alive and feeds the answer back in.
            output["decision"] = "block"
            output["reason"] = answer
        return output
    if state == "pending":
        output["systemMessage"] = (
            f"Ask Human: the question was sent to the human "
            f"(request_id={outcome.get('request_id')}); no answer yet."
        )
        return output
    if state == "skipped":
        output["systemMessage"] = f"Ask Human: nothing to ask ({outcome.get('reason')})."
        return output
    output["systemMessage"] = (
        f"Ask Human: the human could not be reached ({outcome.get('error')}); "
        f"the harness asks directly."
    )
    return output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--event", default=None,
                        help="hook event name (default: the hook_event_name of the payload)")
    parser.add_argument("--timeout", type=float, default=None,
                        help="seconds to wait for the answer (default: ASK_HUMAN_HOOK_TIMEOUT)")
    parser.add_argument("--env-file", default=None,
                        help="protected env file (default: ~/.config/ask-human/env)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        raw = ""
    try:
        payload = json.loads(raw or "{}")
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    event = args.event or str(payload.get("hook_event_name") or "")
    env_file = Path(args.env_file) if args.env_file else None
    settings = resolve_settings(env_file)
    if args.timeout is not None:
        settings["timeout"] = max(args.timeout, 0.0)
    deny_words = tuple(settings["deny_words"])
    try:
        outcome = run(payload, event, settings)
    except Exception as error:  # the hook fails open, and says so
        outcome = {"state": "failed", "error": str(error) or error.__class__.__name__}
    sys.stdout.write(json.dumps(build_output(event, outcome, deny_words), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
