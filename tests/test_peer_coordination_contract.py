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








def test_the_shipped_package_carries_the_same_contract():
    # The package is a generated projection: the contract may never drift from the
    # canonical protocol it was generated from.
    assert PROJECTED.read_text() == CANON.read_text()
    assert (PACKAGE / 'skills/last-human-commit/SKILL.md').read_text() == UMBRELLA.read_text()
    for root in (PACKAGE, PACKAGE / 'native/codex'):
        assert 'session send' in (root / 'common/protocols/COORDINATION.md').read_text()


def test_a_plain_send_to_a_busy_peer_is_a_queue_not_a_delivery():
    # A coordinator once told the whole cluster to write with `sync: false`. That is
    # a queue: the runtime holds the message until the peer's current turn ends, so
    # the message arrived hours later and a worker sat idle while the build window
    # waited on it. "Queued" is not a result.
    protocol = flat(CANON.read_text())
    assert 'A plain send to a busy peer is a queue' in protocol
    assert 'it arrives hours later or never' in protocol
    assert 'Use `force_steer: true` for a peer that is running' in protocol
    assert '"Queued" is not a result' in protocol
    assert 'stands idle is a defect' in protocol
    # The same rule has to be in the always-loaded skill and in the router.


def test_a_supervisor_decides_silently_and_reports_only_exceptions():
    protocol = flat(CANON.read_text())
    assert '## Supervision of other sessions' in protocol
    assert 'decides inside the protocol instead of asking the owner' in protocol
    assert 'wakes a peer that holds the critical path and stands idle' in protocol
    assert "a change of the owner's rules" in protocol
    assert 'a deadlock that did not close in two cycles' in protocol
    assert 'does not merge, rebuild, restart, publish' in protocol
