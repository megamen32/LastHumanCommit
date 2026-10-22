"""A Lead must be able to address a peer session without discovering the channel.

A coordinator session was asked to steer six peer sessions, divide ownership and
explain how the peers write back. It did that correctly — it loaded the umbrella
skill, read the package router and played the Lead — but it spent its discovery
turns rediscovering how a peer is addressed at all: Agent Herder does not know a
native `mvs_...` id, the runtime's own session interface carries the message, a
steered message gets no separate answer, and the receipt is not delivery evidence.
The package must carry that contract, so a Lead reads it instead of probing for it.

The same session had no mode for its own scope: ownership, handoffs and steering
messages are not a code change, not research and not a read-only status answer. The
mode table must name that scope, or the Lead bends an existing mode and skips the
ownership registry that keeps one owner per task, file and runtime.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'plugins/last-human-commit'
CANON = ROOT / 'src/common/protocols/COORDINATION.md'
PROJECTED = PACKAGE / 'common/protocols/COORDINATION.md'
UMBRELLA = ROOT / 'src/common/skills/last-human-commit/SKILL.md'
ROUTER = ROOT / 'AGENTS.md'


def flat(text: str) -> str:
    """Line wrapping must not change what the contract says."""
    return " ".join(text.split())


def test_the_protocol_names_the_channel_that_actually_reaches_a_peer():
    protocol = flat(CANON.read_text())
    # The runtime interface, not a shell command and not Herder.
    assert 'session send' in protocol
    assert 'session messages' in protocol
    assert 'session list' in protocol
    assert 'force_steer' in protocol
    # The trap that cost the coordinator session its discovery turns.
    assert 'Agent Herder keys sessions by its own native ids' in protocol
    assert 'mvs_...' in protocol
    assert 'answers "not found"' in protocol


def test_the_protocol_pins_the_admission_receipt_and_its_two_modes():
    protocol = flat(CANON.read_text())
    assert 'status: accepted' in protocol
    assert 'mode: activated' in protocol
    assert 'mode: steered' in protocol
    # A steered message has no separate answer, and a resend is a second message.
    assert 'gets no separate answer' in protocol
    assert 'a resend is a second message' in protocol


def test_delivery_is_proved_by_the_peer_answer_not_by_the_receipt():
    protocol = flat(CANON.read_text())
    assert 'Delivery is proven by reading the peer' in protocol
    assert 'not by the receipt' in protocol
    # The expensive wrong turn: hunting the filesystem for the transcript.
    assert 'Do not hunt the filesystem for the transcript' in protocol
    assert 'manifest.json' in protocol
    assert 'partial and stale' in protocol


def test_the_file_chat_is_a_fallback_that_may_not_exist_yet():
    protocol = flat(CANON.read_text())
    assert 'creates the chat directory on its first publish' in protocol
    assert 'must not claim the directory already exists' in protocol


def test_the_ownership_registry_has_one_owner_per_item():
    protocol = flat(CANON.read_text())
    assert 'One task, one file and one runtime have exactly one owner' in protocol
    assert 'publishes the registry before it hands work out' in protocol
    assert 'handed <item> → <owner>' in protocol
    assert '.agents/tasks/' in protocol


def test_the_umbrella_skill_carries_the_coordination_mode():
    skill = UMBRELLA.read_text()
    assert 'coordination' in skill
    assert '## Coordinate peer sessions' in skill
    flat_skill = flat(skill)
    # The mode row must name the accepted scope, not just the word.
    assert 'Other live sessions: ownership, handoffs, steering messages' in flat_skill
    assert 'publish the ownership registry' in flat_skill
    assert 'common/protocols/COORDINATION.md' in flat_skill
    # The peer channel has to be reachable from the only always-loaded entry.
    assert 'force_steer' in flat_skill
    assert 'session messages' in flat_skill
    assert 'does not know a native `mvs_...` id' in flat_skill


def test_the_router_names_the_coordination_mode_and_the_peer_channel():
    router = ROUTER.read_text()
    assert len(router.splitlines()) <= 200
    flat_router = flat(router)
    assert 'quickfix/fullcycle/testing/research/status/coordination' in flat_router
    assert 'Address a peer session through the runtime that owns it' in flat_router
    assert 'does not know a native `mvs_...` id' in flat_router
    assert 'prove a delivery by reading the peer' in flat_router
    assert 'exactly one owner; publish the ownership registry' in flat_router


def test_the_lead_role_carries_the_same_contract():
    lead = flat((ROOT / 'src/common/agents/Lead.md').read_text())
    assert 'force_steer' in lead
    assert 'session messages' in lead
    assert 'not the receipt, as proof of delivery' in lead
    assert 'one owner per task, file and runtime' in lead
    assert 'src/common/protocols/COORDINATION.md' in lead


def test_the_shipped_package_carries_the_same_contract():
    # The package is a generated projection: the contract may never drift from the
    # canonical protocol it was generated from.
    assert PROJECTED.read_text() == CANON.read_text()
    assert (PACKAGE / 'skills/last-human-commit/SKILL.md').read_text() == UMBRELLA.read_text()
    for root in (PACKAGE, PACKAGE / 'native/codex'):
        assert 'session send' in (root / 'common/protocols/COORDINATION.md').read_text()
