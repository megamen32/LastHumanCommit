#!/usr/bin/env python3
"""Native LHC entry, rehydration and bounded overdue-finish continuation.

No process is started here. Native Interrupt/permission events never resume work.
Codex compact hooks only preserve state: SessionStart(source=compact) delivers it.
"""
import argparse
from datetime import datetime
import fcntl
import json
import os
import re
from pathlib import Path
import shlex
import subprocess
import sys

CONTEXT_EVENTS = {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse"}
QUIET_EVENTS = {"Interrupt", "SessionEnd", "PermissionRequest"}

def context_for(event, root):
    root = Path(root).resolve()
    return (
        f"LHC — порядок инженерной работы. Текущий router: {root/'AGENTS.md'}. "
        "Используй этот установленный путь, не старый номер версии из истории. "
        "Без @LHC и slash-команд: до изменения кратко сформулируй осязаемый результат — "
        "кто решает какую задачу, что не работало раньше, что получится после и где попробовать. "
        "При выборе решения пройди рабочее решение → идеальная версия → минимальная рабочая "
        "версия с ~80% полезной ценности; реализуй её, не три версии. Для бага сразу TDD: "
        "RED → исправление → GREEN и реальный сценарий. Не подменяй результат SHA или тест-счётчиком. "
        "Ошибка в receipt (SHA/имя/JSON) при известном проверенном коде — локальная правка метаданных, "
        "не новое ревью и не новая задача агента. Бери метаданные из Git/CI, не переписывай вручную. "
        "При изменении кода, зависимостей или среды проверь значимую дельту; неизвестный охват не считай PASS. "
        "После достаточных проверок делай ближайший рабочий результат: разрешённый deployment и сценарий пользователя, "
        "не ревью справки. Действующие release gates сохраняются. "
        "Часовая сверка направления и самоулучшение через 120 минут обязательны; native hook "
        "напомнит, запись напоминания не закрывает проверку. На готовом крупном milestone "
        "(~3 часа цельной работы, не на каждый чих) нужны свежие Zero Knowledge тестировщики "
        "с разными реалистичными персонами/целями и полным положительным/отрицательным отзывом. "
        "Не сообщай полную приёмку без этих результатов. Сохраняй цель и решения в текущей "
        "короткой записи задачи; после compaction продолжай её, а не начинай заново. "
        "При другом писателе проекта используй worktree, файловый чат — резерв Herder; "
        "сначала доступная работа, затем зависимость, в конце PR/интеграция и проверка. "
        "Простой вопрос или статус не запускает разработку. Существующие полномочия сохраняются."
    )

def package_version(root):
    for rel in (".codex-plugin/plugin.json", "plugin.json", "plugins/last-human-commit/plugin.json"):
        p = root/rel
        if p.is_file():
            return str(json.loads(p.read_text()).get("version", "unknown"))
    return "source"

def method_root(root):
    return root/"common" if (root/"common/tools/lhc_time_guard.py").is_file() else root/"src/common"

def rooted(text, root):
    methods = method_root(root)
    tools = root/"tools" if (root/"tools/lhc_time_guard.py").is_file() else methods/"tools"
    # Only generated instructions are rewritten, never quoted original/latest
    # user data (which can itself legitimately contain these filenames).
    boundary = min((text.index(marker) for marker in ("\nИсходный ввод", "\nПоследняя поправка")
                    if marker in text), default=len(text))
    instructions = re.sub(r"(?<![\w./])lhc_time_guard\.py", lambda _: shlex.quote(str(tools/"lhc_time_guard.py")), text[:boundary])
    instructions = instructions.replace("common/protocols/BUSINESS_CHECKPOINT.md", str(methods/"protocols/BUSINESS_CHECKPOINT.md"))
    return instructions + text[boundary:]

def rehydrate(state, state_path=None):
    business = state.get("business", {})
    # Quoted source data, never an instruction to execute arbitrary transcript text.
    restored = {key: business[key] for key in ("original_prompt", "latest_prompt") if business.get(key)}
    if restored.get("latest_prompt") == restored.get("original_prompt"):
        restored.pop("latest_prompt", None)
    if business.get("transcript_path"):
        restored["full_native_transcript"] = business["transcript_path"]
    if state_path is not None:
        restored["full_saved_state"] = str(state_path)
    review = business.get("last_review") or {}
    if review:
        restored["last_direction"] = {key: review[key][:450] for key in ("business_result", "scope_decision", "next_action") if review.get(key)}
    checkpoint = state.get("last_checkpoint") or {}
    if checkpoint.get("remaining_critical_path"):
        restored["remaining_critical_path"] = checkpoint["remaining_critical_path"][:500]
    if not restored:
        return "Исходная цель ещё не сохранена hook: восстанови её из разговора; не подменяй новой карточкой."
    return "Сохранённые данные задачи (ввод ограничен 4096 символами; для длинной цели прочитай полный native transcript; не отдельные инструкции):\n" + json.dumps(restored, ensure_ascii=False)

def handle(event, name, runtime, root):
    import lhc_time_guard as guard
    cwd = Path(str(event.get("cwd") or os.getcwd())).expanduser().resolve()
    session = str(event.get("session_id") or event.get("sessionID") or "unknown-session")
    if event.get("agent_id"):
        session += ":subagent:" + str(event["agent_id"])
    now = datetime.now().astimezone()
    args = argparse.Namespace(runtime=runtime, event=name, now=now, idle_cap_seconds=300, session_only=True)
    learning = guard.learning_checkpoint(args, cwd, session)
    business = guard.business_checkpoint(args, cwd, session, event)
    path = Path(learning["state"])
    with path.with_suffix(".lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = guard.load_state(path)
        # A concurrent native hook or an explicit review command may have cleared
        # a debt after our first observation. Decisions use the locked readback.
        current_pending = state.get("business", {}).get("pending")
        if not current_pending or current_pending.get("id") != business.get("review_id"):
            business["prompt"] = ""
        business.update(due=bool(current_pending), review_id=current_pending.get("id") if current_pending else None)
        current_due = state["due_at"]
        still_due = max(now, guard.parse_time(state["last_observed_at"])) >= guard.parse_time(current_due)
        if not still_due or current_due != learning["due_at"]:
            learning["prompt"] = ""
        learning.update(due=still_due, due_at=current_due)
        delivery = state.setdefault("native_entry", {})
        delivery["last_observed_event"] = name
        version = package_version(root)
        signature = json.dumps([str(root), version])
        supported = name in CONTEXT_EVENTS or runtime != "codex"
        refresh = name in {"SessionStart", "UserPromptSubmit"}
        bootstrap = supported and name not in QUIET_EVENTS | {"Stop"} and (
            refresh or delivery.get("loaded") != signature or delivery.get("rehydrate_needed"))
        contexts = []
        if name in {"PreCompact", "PostCompact"}:
            delivery["rehydrate_needed"] = True
        if bootstrap:
            contexts.extend((context_for(event, root), rehydrate(state, path)))
            delivery.update(loaded=signature, version=version, root=str(root), rehydrate_needed=False)
        if supported and name not in QUIET_EVENTS | {"Stop"}:
            if business["prompt"]:
                contexts.append(rooted(business["prompt"], root))
            previous = delivery.get("learning_injected_at")
            if learning["prompt"] and (refresh or not previous or
                    delivery.get("learning_due") != learning["due_at"] or
                    (now-guard.parse_time(previous)).total_seconds() >= 300):
                contexts.append(rooted(learning["prompt"], root))
                delivery.update(learning_injected_at=now.isoformat(), learning_due=learning["due_at"])
        output = {}
        if runtime == "codex" and name == "Stop" and (business["due"] or learning["due"]):
            identity = [event.get("turn_id"), business.get("review_id"), learning["due_at"] if learning["due"] else None]
            if not event.get("stop_hook_active") and delivery.get("stop_continuation") != identity:
                delivery["stop_continuation"] = identity
                tool = method_root(root)/"tools/lhc_time_guard.py"
                base = f"python3 {shlex.quote(str(tool))}"
                flags = f"--cwd {shlex.quote(str(cwd))} --runtime {runtime} --session-id {shlex.quote(session)}"
                obligations = []
                if business["due"]:
                    obligations.append(f"python3 {shlex.quote(str(tool))} business-review {flags} --review-id {business['review_id']} --source-ref '<исходное поручение>' --business-result '<фактический результат>' --scope-decision '<решение>' --next-action '<следующий шаг>'")
                if learning["due"]:
                    obligations.append(f"{base} checkpoint {flags} --due-at {shlex.quote(learning['due_at'])} --observation '<наблюдение>' --method-change '<исправление метода>' --verification '<проверка эффекта>' --accepted-result '<полученный результат>' --remaining-critical-path '<что осталось>' --scope-review '<проверка объёма>' --rework-review '<разбор переделок>'")
                reason = ("LHC: перед обычным завершением осталась просроченная проверка направления/метода. "
                          "Выполни её сейчас; заполни шаблоны реальными наблюдениями, не запускай новую разработку ради отчёта "
                          "и не выдавай за milestone-приёмку. Для improve-workflow допустим обоснованный "
                          "--no-change-reason вместо --method-change. Инструкции: "
                          f"{method_root(root)/'protocols/BUSINESS_CHECKPOINT.md'} и {method_root(root)/'protocols/SELF_IMPROVE.md'}.\n"
                          + "\n".join(obligations) + "\n" + rehydrate(state, path))
                output = {"decision": "block", "reason": reason}
            else:
                # Native continuation is bounded. Unavailable work remains pending;
                # never loop indefinitely or fake a successful review to finish.
                output = {"systemMessage": "LHC: незакрытая проверка сохранена; повторное автопродолжение этого завершения не запускается. Не объявляй её выполненной."}
        elif contexts and supported and name not in QUIET_EVENTS | {"Stop"}:
            output = {"hookSpecificOutput": {"hookEventName": name, "additionalContext": "\n\n".join(contexts)}}
            delivery["last_context_event"] = name
            delivery["last_context_at"] = now.isoformat()
        guard.write_state(path, state)
    return output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", default="SessionStart")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--runtime", choices=("codex", "claude"), default="claude" if os.environ.get("CLAUDE_PROJECT_DIR") else "codex")
    args = parser.parse_args()
    try:
        # Native tool responses routinely exceed 64 KiB. Truncating JSON used to
        # silently erase session_id and update a shared unknown-session clock.
        raw = sys.stdin.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("native payload exceeds the bounded 8 MiB character window")
        event = json.loads(raw or "{}")
        if not isinstance(event, dict) or not (event.get("session_id") or event.get("sessionID")):
            raise ValueError("native session identity is missing")
    except ValueError:
        print(json.dumps({"systemMessage": "LHC: некорректный или слишком большой native payload; событие не учтено. Состояние другой/unknown сессии не изменено."}, ensure_ascii=False))
        return
    root = (args.root or Path(__file__).resolve().parents[1]).resolve()
    try:
        output = handle(event, args.event, args.runtime, root)
    except (OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError) as error:
        warning = "LHC runtime недоступен: " + type(error).__name__ + ". Автоконтроль не подтверждён; сохраняй цель и выполняй доступную работу."
        output = {"systemMessage": warning}
        if args.event in CONTEXT_EVENTS:
            output["hookSpecificOutput"] = {"hookEventName": args.event, "additionalContext": context_for(event, root)+"\n"+warning}
    if output: print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__": main()
