"""Regressions from OmniRoute: direct corrections must survive tool/goal noise."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/common/tools"))
import lhc_progress_review as review


def message(text, **extra):
    return {"type": "response_item", "payload": {"type": "message", "role": "user",
            "content": [{"type": "input_text", "text": text}], **extra}}


def write_log(tmp_path, rows):
    path = tmp_path / "native.jsonl"
    meta = {"type": "session_meta", "payload": {"id": "sid", "cwd": str(tmp_path), "source": "cli"}}
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [meta, *rows]) + "\n")
    return path


def test_correction_outside_tool_tail_survives_automatic_goal_reminders(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "MAX_INPUT", 2048)
    correction = "Сначала Individual в моём OpenCode, затем Start; PR после живой работы."
    supplied = "Start уже работает: session_347b6f79. Больше не проси меня запускать сессию."
    noise = {"type": "response_item", "payload": {"type": "function_call_output", "output": "build log " * 200}}
    goal = message('<codex_internal_context source="goal">Finish PRs and profiles.</codex_internal_context>')
    path = write_log(tmp_path, [message("Доведи OmniRoute до установленного результата."),
                               *([noise] * 3), message(correction), message(supplied),
                               *([noise] * 8), *([goal] * 12)])
    source = review.transcript(path, "sid", tmp_path)
    texts = [row["text"] for row in source["recent_user_messages"]]
    assert correction in texts and supplied in texts
    assert source["latest_user_message"]["text"] == supplied
    assert all("codex_internal_context" not in text for text in texts)
    assert any("codex_internal_context" in json.dumps(row) for row in source["recent_actions_results"])


def test_explicit_peer_relay_does_not_replace_last_direct_correction(tmp_path):
    correction = "Проверь работу через установленный клиент, а не только исходники."
    relay = '🤖 Сообщение от ИИ через Agent Herder\n<agent-herder-origin version="1" kind="agent-relay" transport="deliver" />\nПора готовить PR.'
    path = write_log(tmp_path, [message(correction), message(relay)])
    source = review.transcript(path, "sid", tmp_path)
    assert source["latest_user_message"]["text"] == correction
    assert any(row.get("origin") == "agent-relay" for row in source["recent_actions_results"])
    assert source["latest_user_message"]["origin"] == "unknown"  # unmarked is not authentication


def test_recent_corrections_are_bounded_redacted_and_not_private_reasoning(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "MAX_INPUT", 2048)
    rows = [message("Установи результат.")]
    rows += [message("Поправка " + str(i) + " token=DO_NOT_SHARE") for i in range(20)]
    rows += [{"type": "response_item", "payload": {"type": "message", "role": "assistant", "channel": "analysis",
             "content": [{"type": "output_text", "text": "PRIVATE_REASONING"}]}}]
    source = review.transcript(write_log(tmp_path, rows), "sid", tmp_path)
    assert len(source["recent_user_messages"]) == 8
    snapshot = review.bounded_snapshot({**source, "current_tool": {}, "candidate_plans": [], "previous_advice": None})
    encoded = json.dumps(snapshot, ensure_ascii=False)
    assert len(encoded) <= 64000
    assert "DO_NOT_SHARE" not in encoded and "PRIVATE_REASONING" not in encoded
    assert "Поправка 19" in encoded


def test_unscanned_instruction_history_is_explicitly_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "MAX_INPUT", 1024)
    monkeypatch.setattr(review, "MAX_INSTRUCTION_SCAN", 2048)
    noise = {"type": "response_item", "payload": {"type": "function_call_output", "output": "x" * 500}}
    path = write_log(tmp_path, [message("Исходная задача."), *([noise] * 20), message("Последняя поправка.")])
    source = review.transcript(path, "sid", tmp_path)
    assert source["instruction_history_truncated"] is True
    assert source["latest_user_message"]["text"] == "Последняя поправка."
    assert "unknown" in source["source_window"]


def test_long_native_startup_does_not_hide_the_original_user_request(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "MAX_INPUT", 2048)
    startup = {"type": "response_item", "payload": {"type": "message", "role": "developer",
               "content": [{"type": "input_text", "text": "runtime tools " * 2000}]}}
    path = write_log(tmp_path, [startup, message("Рабочий streaming в моём клиенте, не только direct smoke.")])
    source = review.transcript(path, "sid", tmp_path)
    assert source["initial_user_messages"][0]["text"].startswith("Рабочий streaming")
    assert source["latest_user_message"]["text"] == source["initial_user_messages"][0]["text"]
