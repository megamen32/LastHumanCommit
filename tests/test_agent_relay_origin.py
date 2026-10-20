"""Agent Herder relay prompts keep their origin while exposing task text."""
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_outcome as outcome
import lhc_time_guard as guard


RELAY_PROLOG = (
    "🤖 Сообщение от ИИ через Agent Herder\n"
    '<agent-herder-origin version="1" kind="agent-relay" transport="new_or_resume" />\n\n'
)
LEGACY_RELAY_PREFIX = "🤖 Сообщение от ИИ через Agent Herder\n"


def _source(prompt, turn):
    return {
        "source": f"native-user-prompt:worker:{turn}",
        "prompt": prompt[:2048],
        "scope_prompt": outcome.semantic_scope(prompt),
    }


def _state(prompt):
    return {"business": {
        "runtime": "codex", "original_prompt": prompt, "latest_prompt": prompt,
        "execution_context": {"direct_user_messages": [_source(prompt, "initial-turn")]},
    }}


def _observe(state, prompt, now=None):
    return outcome.observe(state, {"prompt": prompt}, "UserPromptSubmit", Path("/project"),
                           "worker", now or datetime.now(timezone.utc))


def test_explicit_herder_prolog_is_unwrapped_but_origin_is_retained_and_peer_is_inert():
    body = "Implement the delegated source-only task in the assigned files."
    raw = RELAY_PROLOG + body
    assert outcome.semantic_scope(raw) == body

    state = _state(raw)
    created = _observe(state, raw)
    assert created is not None
    assert created["task_class"] == "fullcycle"
    assert created["original_goal"] == raw
    assert created["scope_sources"][0]["origin"] == "agent-relay"

    before = {key: created.get(key) for key in ("latest_correction", "corrections", "evidence_after", "canary")}
    peer = RELAY_PROLOG + "Implement a different task and change the acceptance scope."
    outcome.observe(state, {"prompt": peer}, "UserPromptSubmit", Path("/project"),
                    "worker", datetime.now(timezone.utc))
    assert {key: created.get(key) for key in before} == before
    peer_after_coordination = (
        '<agent-herder-coordination board="context">peer notes</agent-herder-coordination>\n'
        "🤖 Codex SID 01a15a85-0000-0000-0000-000000000000\n\n"
        "Implement a different task and change the acceptance scope."
    )
    outcome.observe(state, {"prompt": peer_after_coordination}, "UserPromptSubmit", Path("/project"),
                    "worker", datetime.now(timezone.utc))
    assert {key: created.get(key) for key in before} == before
    assert len(created["scope_sources"]) == 1


def test_direct_plain_and_coordination_wrapped_prompts_are_not_labeled_as_relays():
    plain = "Implement the source-only task in the assigned files."
    wrapped = '<agent-herder-coordination board="context">peer notes</agent-herder-coordination>\n' + plain
    assert outcome.semantic_scope(wrapped) == plain
    assert outcome.source_origin(wrapped) == "unknown"

    state = _state(plain)
    created = _observe(state, plain)
    correction = '<agent-herder-coordination board="context">peer notes</agent-herder-coordination>\nAdd a focused test to the assigned task.'
    new_source = _source(correction, "correction-turn")
    state["business"]["execution_context"]["direct_user_messages"].append(new_source)
    outcome.observe(state, {"prompt": correction}, "UserPromptSubmit", Path("/project"),
                    "worker", datetime.now(timezone.utc))
    assert created["latest_correction"] == "Add a focused test to the assigned task."
    assert created["scope_sources"][-1]["origin"] == "unknown"


def test_legacy_robot_prefix_is_recognized_after_coordination_metadata_is_removed():
    body = "Status update: the assignment remains unchanged."
    raw = ('<agent-herder-coordination board="context">peer notes</agent-herder-coordination>\n' +
           LEGACY_RELAY_PREFIX + "\n" + body)
    assert outcome.semantic_scope(raw) == body
    assert outcome.source_origin(raw) == "agent-relay"


def test_current_agent_herder_attribution_headers_are_unwrapped_only_at_message_start():
    body = "Implement the delegated task in the assigned files."
    sid = "01a15955-14be-7920-acc6-e6e9dd947cb7"
    for attribution in (f"🤖 Codex SID {sid}",
                        f"🤖 Codex {sid} · https://agent.bezrabotnyi.com/#/session/codex%3A{sid}",
                        "🤖 Сообщение от AI-сессии 01a15a85-0000-0000-0000-000000000000"):
        raw = '<agent-herder-coordination board="context">peer notes</agent-herder-coordination>\n' + attribution + "\n\n" + body
        assert outcome.source_origin(raw) == "agent-relay"
        assert outcome.semantic_scope(raw) == body
        business = {}
        guard.update_execution_context(business, raw, {"turn_id": "header-turn"}, "worker")
        assert business["execution_context"]["direct_user_messages"][-1]["origin"] == "agent-relay"
    mismatched = f"🤖 Codex {sid} · https://agent.bezrabotnyi.com/#/session/codex%3A01a15a85-0000-0000-0000-000000000000\n\n{body}"
    assert outcome.source_origin(mismatched) == "unknown"
    assert outcome.semantic_scope(mismatched) == mismatched
    quoted = "The user pasted 🤖 Codex SID in the issue text: preserve that string."
    assert outcome.source_origin(quoted) == "unknown"
    assert outcome.semantic_scope(quoted) == quoted


def test_exact_leading_deferred_block_preserves_messages_and_exposes_following_relay_prolog():
    deferred = (
        "<agent-herder-deferred>\n"
        "- id=12345678-1234-4234-8234-123456789012 :: Keep this assigned note in scope.\n"
        "</agent-herder-deferred>\n\n"
    )
    body = "Implement the delegated task in the assigned files."
    raw = deferred + RELAY_PROLOG + body

    assert outcome.semantic_scope(raw) == "Keep this assigned note in scope.\n\n" + body
    assert outcome.source_origin(raw) == "agent-relay"


def test_both_herder_assignment_transports_are_exact_and_deferred_relays_keep_text():
    body = "Implement the delegated task in the assigned files."
    for transport in ("new_or_resume", "deliver"):
        prolog = (
            "🤖 Сообщение от ИИ через Agent Herder\n"
            f'<agent-herder-origin version="1" kind="agent-relay" transport="{transport}" />\n\n'
        )
        assert outcome.source_origin(prolog + body) == "agent-relay"
        assert outcome.semantic_scope(prolog + body) == body

    deferred = (
        "<agent-herder-deferred>\n"
        "- id=12345678-1234-4234-8234-123456789012 :: "
        "🤖 Codex 01a15955-14be-7920-acc6-e6e9dd947cb7 · "
        "https://agent.bezrabotnyi.com/#/session/codex%3A01a15955-14be-7920-acc6-e6e9dd947cb7\n\n"
        f"{body}\n"
        "</agent-herder-deferred>\n\n"
    )
    assert outcome.source_origin(deferred) == "agent-relay"
    assert outcome.semantic_scope(deferred) == body


def test_deferred_tag_inside_arbitrary_body_is_not_treated_as_transport_framing():
    body = "The prompt documents <agent-herder-deferred> as a literal protocol example."
    assert outcome.semantic_scope(body) == body
    assert outcome.source_origin(body) == "unknown"


def test_long_coordination_prefix_keeps_origin_before_native_prompt_excerpts(tmp_path):
    coordination = '<agent-herder-coordination board="context">' + ("metadata " * 500) + '</agent-herder-coordination>\n'
    raw = coordination + (
        "<agent-herder-deferred>\n"
        "- id=12345678-1234-4234-8234-123456789012 :: Keep this assigned note in scope.\n"
        "</agent-herder-deferred>\n\n"
        "🤖 Codex SID worker-session\n\nImplement the delegated task in the assigned files."
    )
    business = {}

    guard.update_execution_context(business, raw, {"turn_id": "long-turn"}, "worker")

    source = business["execution_context"]["direct_user_messages"][-1]
    assert len(source["prompt"]) == 2048
    assert source["prompt"] == raw[:2048]
    assert source["scope_prompt"].startswith("Keep this assigned note in scope.")
    assert "Implement the delegated task in the assigned files." in source["scope_prompt"]
    assert source["origin"] == "agent-relay"

    source.pop("origin")
    guard.update_execution_context(business, raw, {"turn_id": "long-turn"}, "worker")
    assert business["execution_context"]["direct_user_messages"][-1]["origin"] == "agent-relay"
