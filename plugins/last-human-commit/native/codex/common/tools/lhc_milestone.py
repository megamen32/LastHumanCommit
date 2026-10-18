"""Durable native milestone debt. Observation only: no actions or scheduling.

Intent comes from human messages, change from Git, feedback from adapter-owned
raw transcripts exported by the existing Herder. Leader prose cannot accept work.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
from urllib.parse import urlparse
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler
from time import monotonic

MAX_BYTES = 8 * 1024 * 1024
UI = re.compile(r"\.(?:html?|css|scss|sass|vue|svelte|jsx|tsx|qml|xaml|dart|swift|xml)$", re.I)
GENERATED_UI = re.compile(r"\.(?:[cm]?[jt]s|py|go|rb|php)$", re.I)
SURFACE = re.compile(r"\b(?:ui|ux|web|website|dashboard|frontend|interface|screen|page|portal|landing|app|visual|layout|responsive|form)\b|интерфейс|экран|страниц|кабинет|сайт|приложен|дашборд|лендинг|визуал|форм[ау]|дизайн", re.I)
BUILD = re.compile(r"\b(?:build|create|implement|redesign|rebuild|develop|complete|improve)\b|создай|сделай|реализуй|разработ|переделай|переработ|улучши", re.I)
SMALL = re.compile(r"\b(?:small|minor|tiny|typo|padding|spacing)\b|опечат|отступ|мелк|небольш", re.I)
READ_ONLY = re.compile(r"\b(?:read.only|review only|you are .{0,30}(?:tester|reviewer)|zero knowledge tester|do not (?:edit|modify) code|no code changes)\b|только (?:прочитай|ревью|провер|тест)|ты .{0,25}тестировщик|не (?:меняй|редактируй) код", re.I)
ACCEPT = re.compile(r"(?:final|milestone|explicit|user) acceptance|(?:итогов|финальн|пользовательск).{0,20}при[её]мк|focus.groups|фокус.групп", re.I)
URL = re.compile(r"https?://[^\s<>\]\)\"']+", re.I)
POSITIVE = re.compile(r"\bpositive\b|\bliked\b|what helped|(?<!не )понрав|(?<!не )\bпомог|\bудобно\b", re.I)
NEGATIVE = re.compile(r"negative|disliked|confus|frustrat|не понрав|мешал|неудоб|затруд|недостат|критик", re.I)
ACHIEVED = re.compile(r"(?:goal|task) (?:was )?(?:achieved|completed)|цель достигнута|задача выполнена|\bPASS\b", re.I)
BLOCKED = re.compile(r"blocked|not.tested|блокир|заблокир|не протестирован|STOP_MISSING_REAL_SURFACE", re.I)
ACCESS = re.compile(r"login|log.in|sign.in|authenticat|credentials|permission|авторизац|вход|уч[её]тн|доступ|разрешен", re.I)
CHANGES = re.compile(r"changes.required|goal (?:was )?not achieved|цель не достигнута|нужны исправления", re.I)
PARTIAL = re.compile(r"\bpartial\b|not.tested|never (?:attempted|tested)|did not (?:test|attempt|complete|import)|(?:required|assigned).{0,60}(?:failed|untested)|частичн|не (?:проверил|протестировал|пытался|импортировал)", re.I)

def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()

def minor(goal):
    return bool(SMALL.search(goal) and not re.search(r"\b(?:full|complete|major|entire)\b|полност|целиком|крупн", goal, re.I))

def task_flags(goal):
    # Intent must describe an action on a user surface in the same human
    # sentence. A quoted workflow requirement elsewhere is not a UI assignment.
    sentences = re.split(r"\n|(?<=\.)\s+", goal)
    expected = any(SURFACE.search(s) and BUILD.search(s) and not minor(s) for s in sentences)
    first = sentences[0] if sentences else ""
    explicit = bool(SURFACE.search(first) and ACCEPT.search(first))
    return bool(expected or explicit), explicit

def read(path):
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("raw source exceeds bounded native window")
    return data

def git(cwd, *args):
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, timeout=2)
    if len(result.stdout) > MAX_BYTES:
        raise ValueError("Git surface exceeds bounded window")
    return result.stdout if result.returncode == 0 else b""

def candidates(cwd, head):
    paths = git(cwd, "diff", "--name-only", "-z", head) if head else git(cwd, "ls-files", "-z")
    paths += git(cwd, "ls-files", "--others", "--exclude-standard", "-z")
    result = []
    for raw in sorted(set(paths.split(b"\0"))):
        if not raw:
            continue
        p = raw.decode()
        if set(Path(p).parts) & {"tests", "test", "__tests__", ".tmp", ".agents", "node_modules"} or re.search(r"(?:^|/)(?:test_|.*\.test\.)", p):
            continue
        if UI.search(p):
            result.append(p)
        elif GENERATED_UI.search(p):
            path = (cwd / p).resolve()
            path.relative_to(cwd)
            data = read(path) if path.is_file() else git(cwd, "show", head + ":" + p)
            if re.search(rb"<(?:!doctype|html|main|body|form|button|input|div)\b|(?:React\.createElement|render_template)\(", data, re.I):
                result.append(p)
    if len(result) > 256:
        raise ValueError("more than 256 changed UI paths; narrow the milestone")
    return result

def file_hash(cwd, name):
    path = (cwd / name).resolve()
    path.relative_to(cwd)
    return digest(read(path)) if path.is_file() else "deleted"

def content(parts):
    if isinstance(parts, str):
        return parts
    if isinstance(parts, list):
        return "\n".join(str(x.get("text", "")) for x in parts if isinstance(x, dict))
    return ""

def native_transcript(data):
    """Codex native JSONL. Unknown/partial formats fail pending, never PASS."""
    rows = [json.loads(line) for line in data.decode().splitlines() if line.strip()]
    meta = next((r["payload"] for r in rows if r.get("type") == "session_meta"), {})
    messages, calls, observations = [], {}, []
    for row in rows:
        p = row.get("payload", {})
        if row.get("type") == "event_msg" and p.get("type") == "item_completed":
            item = p.get("item", {})
            if item.get("type") == "CommandExecution" and item.get("exit_code") == 0:
                command = item.get("command", [])
                if isinstance(command, list) and len(command) >= 3:
                    observations.append(({"name": "exec_command", "arguments": json.dumps({"cmd": command[-1]})},
                                         str(item.get("aggregated_output") or "")))
        if row.get("type") != "response_item":
            continue
        kind = p.get("type", "")
        if kind == "message" and p.get("role") in {"user", "assistant"}:
            text = content(p.get("content"))
            if not text.startswith(("# AGENTS.md instructions", "<environment_context>")):
                messages.append((p["role"], text, p.get("phase")))
        elif kind in {"function_call", "custom_tool_call"}:
            calls[p.get("call_id")] = p
        elif kind in {"function_call_output", "custom_tool_call_output"}:
            call = calls.get(p.get("call_id"), {})
            observations.append((call, content(p.get("output"))))
    return meta, messages, observations

def first_goal(event, state):
    business = state.get("business", {})
    goal = business.get("original_prompt") or event.get("prompt")
    latest = business.get("latest_prompt") or ""
    if latest and not latest.startswith("🤖") and task_flags(latest)[0]:
        goal = latest
    if not goal and event.get("transcript_path"):
        try:
            _, messages, _ = native_transcript(read(event["transcript_path"]))
            goal = next((text for role, text, _ in messages if role == "user"), "")
        except (OSError, ValueError, StopIteration):
            pass
    # OpenCode's canonical context hook can bootstrap an already open thread.
    if not goal:
        goal = next((content(m.get("content")) for m in event.get("messages", [])
                     if isinstance(m, dict) and m.get("role") == "user"), "")
    return goal if isinstance(goal, str) else ""

def observe(state, event, name, cwd, session, now):
    milestone = state.get("milestone")
    goal = first_goal(event, state)
    human_prompt = str(event.get("prompt") or "") if name == "UserPromptSubmit" and not event.get("_lhc_control_prompt") else ""
    # A later human can start a UI outcome in an existing non-UI session. Status,
    # corrections and peer envelopes do not replace its accepted assignment.
    new_ui_task = bool(human_prompt and not human_prompt.startswith("🤖") and SURFACE.search(human_prompt)
                       and (BUILD.search(human_prompt) or re.search(r"\b(?:fix|adjust|change)\b|исправ|поправ", human_prompt, re.I) or ACCEPT.search(human_prompt))
                       and (not milestone or human_prompt != milestone["goal"]))
    if new_ui_task and milestone:
        if pending(milestone):
            if human_prompt not in milestone["goal"]:
                milestone["goal"] = (milestone["goal"] + "\n" + human_prompt)[-8192:]
        else:
            milestone = None
            goal = human_prompt
    if not milestone and goal:
        head = git(cwd, "rev-parse", "--verify", "HEAD").decode().strip()
        baseline = {p: file_hash(cwd, p) for p in candidates(cwd, head)} if name == "UserPromptSubmit" else {}
        milestone = state["milestone"] = {
            "task": digest(session + "\n" + goal)[:20], "goal": goal[:4096],
            "started_at": now.isoformat(), "head": head, "baseline": baseline,
            "expected": task_flags(goal)[0], "explicit": task_flags(goal)[1],
            "read_only": bool(READ_ONLY.search(goal[:500])), "cwd": str(cwd),
            "status": "not-required", "surface": {}, "sources": [], "feedback": [],
        }
    if not milestone:
        return None
    if name == "PostToolUse":
        # export_transcript returns a navigation card, often outside product CWD:
        # Herder's MCP-process workspace owns the archive. Persist its exact path.
        for text in response_texts(event.get("tool_response")):
            for match in re.finditer(r"Lineage manifest:\s*([^\r\n]+\.manifest\.json)", text):
                path = match[1].strip()
                if Path(path).is_absolute() and path not in milestone["sources"]:
                    milestone["sources"] = (milestone["sources"] + [path])[-16:]
    if name in {"Interrupt", "SessionEnd", "PermissionRequest", "session.error", "ToolFailure"}:
        milestone["hold"] = name
    elif (name == "UserPromptSubmit" and not event.get("_lhc_control_prompt")) or name == "permission.replied":
        milestone.pop("hold", None)
    elif name == "PostToolUse" and tool_failed(event):
        milestone["hold"] = "ToolFailure"
    elif name == "PostToolUse" and milestone.get("hold") in {"ToolFailure", "PermissionRequest"}:
        milestone.pop("hold", None)
    if milestone["read_only"]:
        return milestone
    # Deployment/start URL belongs to the current runnable task, not necessarily
    # the user's first sentence. Read this existing small project note only.
    urls = URL.findall(milestone["goal"])
    local_run = cwd / "LOCAL_RUN.md"
    if not urls and local_run.is_file() and not local_run.is_symlink():
        urls = URL.findall(read(local_run).decode())
    milestone["urls"] = urls
    # Reconcile observable repository changes, never keywords in tool stdout.
    surface = {}
    for p in sorted(set(candidates(cwd, milestone["head"])) | set(milestone["surface"])):
        value = file_hash(cwd, p)
        original = milestone["baseline"].get(p)
        if original is None:
            old = git(cwd, "show", milestone["head"] + ":" + p) if milestone["head"] else b""
            original = digest(old)
        if value != original:
            surface[p] = value
    # A broad implementation with several UI components is also a milestone,
    # even when the human did not use the words UI or milestone.
    required = milestone["expected"] or (len(surface) >= 3 and bool(BUILD.search(milestone["goal"])) and not minor(milestone["goal"]))
    if not required or not (surface or milestone["explicit"] or milestone.get("surface_key")):
        return milestone
    key = digest(json.dumps(surface, sort_keys=True) + milestone["task"] + milestone["goal"])[:20]
    if milestone.get("surface_key") != key:
        milestone.update(surface=surface, surface_key=key, changed_at=now.isoformat(), status="pending", feedback=[])
        milestone.pop("blocker", None)
    if pending(milestone) and not milestone.get("hold") and (name in {"Stop", "PreCompact"} or event.get("model_boundary")):
        reconcile_feedback(milestone, cwd, session)
    final = str(event.get("last_assistant_message") or "")
    if name == "Stop" and BLOCKED.search(final) and (ACCESS.search(final) or "STOP_MISSING_REAL_SURFACE" in final):
        milestone.update(status="blocked", blocker=final[:2000])
    return milestone

def tool_failed(event):
    response = event.get("tool_response")
    return bool(event.get("error") or (isinstance(response, dict) and
        (response.get("isError") or response.get("exit_code", 0) not in {0, None})))

def response_texts(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from response_texts(child)
    elif isinstance(value, dict):
        for key in ("content", "text", "output", "stdout", "result"):
            if key in value:
                yield from response_texts(value[key])

def archive_sources(cwd, milestone):
    # Herder owns these raw exports/manifests already; no new receipt store.
    local = (cwd / ".agent-herder/transcripts").glob("*/*.manifest.json")
    paths = {p for p in [*local, *(Path(p) for p in milestone["sources"])] if p.is_file()}
    return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)[:16]

def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("missing native timezone")
    return parsed

def browser_attempt(observations, urls):
    navigated, interacted, saw_result = False, False, False
    before = ""
    for call, output in observations:
        name = call.get("name", "").lower().split(".")[-1].rsplit("__", 1)[-1]
        args = str(call.get("arguments") or call.get("input") or "")
        # Real browser tool output or an actual browser CLI operation; a test
        # runner/echo/leader claim is insufficient. Never run these commands here.
        browser = "browser" in name or "agent-device" in name
        action = name
        if name in {"exec_command", "shell_command", "exec", "bash"}:
            try:
                payload = json.loads(args)
                command = payload.get("cmd") or payload.get("command") or ""
                tokens = shlex.split(command)
                if tokens and Path(tokens[0]).name == "ssh":
                    # A managed remote browser operation is still a native
                    # executed command; support ssh's quoted remote argv.
                    remote = next((i for i, token in enumerate(tokens[1:], 1) if "agent-browser" in token), None)
                    tokens = shlex.split(tokens[remote]) + tokens[remote+1:] if remote is not None else []
            except (ValueError, TypeError):
                tokens = []
            # Options such as --session NAME precede the action. Reject echo,
            # test runners and shell scripts containing a quoted browser command.
            browser = bool(tokens and Path(tokens[0]).name in {"agent-browser", "agent-device"})
            action = next((x for x in tokens[1:] if x in {"open", "snapshot", "click", "fill", "type", "press", "select", "screenshot"}), "")
        if not browser or not output or re.search(r"(?:isError|exit_code)\W*[:=]\W*(?:true|[1-9])", output, re.I):
            continue
        if any(url.rstrip("/") in args or url.rstrip("/") in output for url in urls) and re.search(r"open|navigate", action):
            navigated = True
        if navigated and re.search(r"click|fill|type|press|select", action):
            interacted = True
        if navigated and re.search(r"button|textbox|heading|link|кнопк|поле", output, re.I):
            if re.search(r"(?:heading|title).*?(?:log.in|sign.in|вход|авторизац)", output, re.I):
                continue
            if interacted and before and output.strip() != before:
                saw_result = True
            elif not interacted:
                before = output.strip()
    return navigated and interacted and saw_result

def goal_report(final, goal):
    # A mechanical floor, not an LLM semantic grader. Require the actual goal,
    # attempted steps and an observed result, retaining all raw criticism.
    stop = {"build", "create", "complete", "implement", "with", "that", "this", "then", "from", "goal", "task", "acceptance", "user", "final", "surface", "please", "should", "must", "сделай", "создай", "чтобы", "нужно", "должен"}
    terms = {w.casefold() for w in re.findall(r"[^\W\d_]{4,}", goal)} - stop
    shared = sum(bool(re.search(re.escape(word), final, re.I)) for word in terms)
    steps = re.search(r"\b(?:clicked|typed|entered|selected|opened|imported|searched|submitted|pressed|filled)\b|нажал|вв[её]л|импортировал|открыл|выбрал|отправил", final, re.I)
    result = re.search(r"\b(?:saw|found|displayed|appeared|showed|downloaded|observed)\b|увидел|показ|появ|наш[её]л|скачал|результат", final, re.I)
    return shared >= min(2, len(terms)) and bool(terms and steps and result)

def feedback_from(path, milestone, session):
    manifest = json.loads(read(path))
    if manifest.get("format") != "agent-herder-transcript-manifest-v1":
        return None
    target = manifest["target"]
    raw = read(target["path"])
    # Read adapter-owned native source, not a leader-authored summary. A live
    # source may have appended after the export; the exported prefix stays valid.
    if target.get("harness") == "codex" and target.get("complete"):
        location = Path(target["source"]["location"]).resolve()
        native_root = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "sessions"
        location.relative_to(native_root.resolve())
        if target["source"].get("kind") != "native-file" or location.suffix != ".jsonl":
            return None
        native = read(location)
        if not native.startswith(raw):
            return None
        meta, messages, observations = native_transcript(raw)
    elif target.get("harness") == "opencode":
        meta, messages, observations = opencode_transcript(target, raw)
    else:
        return None
    sid = meta.get("id") or meta.get("session_id")
    if not sid or sid == session or sid != target.get("sessionId"):
        return None
    if Path(meta.get("cwd", "/unknown")).resolve() != Path(milestone["cwd"]).resolve():
        return None
    if timestamp(meta["timestamp"]) < timestamp(milestone["changed_at"]):
        return None
    prompt = next((text for role, text, _ in messages if role == "user"), "")
    # Ordinary tester assignment carries the unchanged goal and changed surface
    # reference from current task context. These are correlation, not signatures.
    correlated = milestone["task"] in prompt and milestone["surface_key"] in prompt
    # Existing normal task assignments can carry the literal goal instead of
    # internal references. No leader-written acceptance certificate is needed.
    if not correlated and milestone["goal"] not in prompt:
        return None
    persona = re.search(r"(?:persona|персона)\s*:\s*([^\n]+)|(?:you are|ты)\s+([^\n]+)", prompt, re.I)
    persona_text = next((p.strip() for p in persona.groups() if p), "") if persona else ""
    if len(persona_text) < 15:
        return None
    final = next((text for role, text, phase in reversed(messages) if role == "assistant" and phase != "commentary"), "")
    if len(final) < 100 or not POSITIVE.search(final) or not NEGATIVE.search(final):
        return None
    urls = milestone.get("urls") or URL.findall(prompt)
    if not urls:
        return None
    status = "pending"
    if BLOCKED.search(final) and (ACCESS.search(final) or "STOP_MISSING_REAL_SURFACE" in final):
        status = "blocked"
    elif browser_attempt(observations, urls):
        if CHANGES.search(final):
            status = "changes-required"
        elif ACHIEVED.search(final) and not PARTIAL.search(final) and goal_report(final, milestone["goal"]):
            status = "accepted"
    return {"session": sid, "persona": persona_text, "status": status,
            "source": str(path), "raw_feedback": final, "surface": milestone["surface_key"], "started_at": meta["timestamp"]}

def reconcile_feedback(milestone, cwd, session):
    feedback, sessions, personas = [], set(), set()
    started = monotonic()
    for path in archive_sources(cwd, milestone):
        if monotonic() - started > 2:
            break  # Leave unobserved acceptance pending; native hook is bounded.
        try:
            result = feedback_from(path, milestone, session)
        except (OSError, ValueError, KeyError, TypeError, StopIteration):
            continue
        if result and result["session"] not in sessions:
            sessions.add(result["session"])
            feedback.append(result)
            personas.add(result["persona"].casefold())
    milestone["feedback"] = feedback
    failures = [r for r in feedback if r["status"] != "accepted"]
    latest_failure = max((timestamp(r["started_at"]) for r in failures), default=None)
    successful = [r for r in feedback if r["status"] == "accepted" and
                  (latest_failure is None or timestamp(r["started_at"]) > latest_failure)]
    if len(successful) >= 2 and len({r["persona"].casefold() for r in successful}) >= 2:
        milestone["status"] = "accepted"
    else:
        milestone["status"] = ("changes-required" if any(r["status"] == "changes-required" for r in feedback)
            else "blocked" if any(r["status"] == "blocked" for r in feedback) or milestone.get("blocker") else "pending")

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def native_get(url):
    # Only the existing local native OpenCode read API, no credentials, writes,
    # implicit login, remote hosts or redirects. Failure leaves evidence pending.
    with build_opener(ProxyHandler({}), NoRedirect).open(url, timeout=0.3) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("native API exceeds bounded window")
    result = json.loads(data)
    return result.get("data", result) if isinstance(result, dict) else result

def opencode_transcript(target, raw):
    """Herder exports the message API with partial coverage. Verify freshness
    against native session metadata and archived messages against the same API;
    unknown pagination never becomes evidence of a fresh independent session.
    """
    source = target["source"]
    parsed = urlparse(source["location"])
    sid = target["sessionId"]
    if (source.get("kind") != "native-api" or parsed.scheme != "http" or
            parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.username or parsed.password or
            not re.fullmatch(r"/(?:api/)?session/" + re.escape(sid) + r"/message", parsed.path)):
        raise ValueError("not the local native session message source")
    archived = json.loads(raw)
    live = native_get(source["location"])
    info = native_get(parsed._replace(path=parsed.path.removesuffix("/message"), query="").geturl())
    if info.get("id") != sid or not isinstance(archived, list) or not isinstance(live, list):
        raise ValueError("native session identity unavailable")
    by_id = {(m.get("info") or m).get("id"): m for m in live}
    if any(not (m.get("info") or m).get("id") or by_id.get((m.get("info") or m).get("id")) != m for m in archived):
        raise ValueError("export does not match native messages")
    created = info["time"]["created"] / 1000
    meta = {"id": sid, "timestamp": datetime.fromtimestamp(created).astimezone().isoformat(),
            "cwd": (info.get("location") or {}).get("directory") or info.get("directory")}
    messages, observations = [], []
    for message in archived:
        header = message.get("info") or message
        if header.get("sessionID", sid) != sid:
            raise ValueError("mixed native sessions")
        role = header.get("role") or header.get("type")
        parts = message.get("parts") or message.get("content") or []
        text = content(parts) or message.get("text", "")
        if role in {"user", "assistant"}:
            # Tool-bearing assistant messages are working observations, not the
            # final raw feedback; a later plain assistant answer must conclude.
            has_tools = isinstance(parts, list) and any(p.get("type") == "tool" for p in parts)
            messages.append((role, text, "commentary" if has_tools else None))
        if isinstance(parts, list):
            for part in parts:
                state = part.get("state") or {}
                if part.get("type") == "tool" and state.get("status") == "completed":
                    observations.append(({"name": part.get("tool") or part.get("name") or "", "arguments": json.dumps(state.get("input", {}))}, content(state.get("output"))))
    return meta, messages, observations

def pending(milestone):
    return bool(milestone and milestone["status"] in {"pending", "changes-required", "blocked"})

def reminder(milestone):
    return ("LHC: пользовательская приёмка milestone ещё не завершена (" + milestone["status"] + "). "
        "Не объявляй UI готовым по своим тестам, запуску дочерней сессии или странице входа. "
        "Подготовь разрешённый sandbox/test identity до попыток; не извлекай секреты, не обходи permissions. "
        "Через существующий Herder нужны минимум две свежие независимые Zero Knowledge попытки с разными "
        "реалистичными персонами и полным raw feedback: что понравилось/помогло и что мешало/не понравилось, "
        "наблюдаемые действия и достигнута ли цель. Используй существующий model-routing. "
        "В обычное задание тестировщику включи Persona: <возраст, опыт, цель, условия>, исходную цель/URL "
        "и ссылки текущей задачи/поверхности: " + milestone["task"] + " / " + milestone["surface_key"] + ". "
        "Прочитай исходные ответы штатным Herder export_transcript; hook сохранит возвращённый Lineage manifest "
        "по его фактическому пути без ручного переноса файлов. "
        "Не сочиняй PASS и не создавай новую форму отчёта. Замечания требуют исправления и свежей попытки; "
        "login-only означает blocked/not-tested. Если доступ реально заблокирован, заверши с точной причиной "
        "и неполной приёмкой; повторных автозапусков не будет. Независимую разрешённую работу продолжай. "
        "Изменённая поверхность: " + ", ".join(milestone["surface"]) + ".")
