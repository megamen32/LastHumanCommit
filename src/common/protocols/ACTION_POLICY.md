# ACTION_POLICY

Action policy: what an agent may do on its own authority. This file is the single
source of truth for action autonomy. When an older protocol, tool description or
hook text forbids an action class described here, this file wins: the older text
is incident precedent, not canon. A plan may tighten a rule for one task with the
owner's word; nothing may loosen the invariants. Incidents produce guards that
make an action safe, never new blanket "never"s (see PRODUCT-PHILOSOPHY.md).

## Invariants

1. **No duplicate external effect.** One message content reaches one chat once.
   The guard is the attempt's immutable request_id (inputId): a retry re-sends
   the exact persisted payload under the same id, and the transport treats a
   repeated inputId as the same input, never a second send.
2. **Irreversible or foreign-owned actions need the owner's word.** Merge into a
   foreign main, deletion, money, production, credentials, a live human's queue.
   An existing scoped instruction counts; do not ask for the same permission again.
3. **Every attempt records an open-text cause.** A cause is a free-form string
   end to end; codes are labels added on top, never a filter. No gate may drop,
   replace or generalize a cause it does not recognize. "UNKNOWN" means "no
   cause reached this layer"; the layer must say so instead of inventing one.
4. **The policy stays small.** A new rule lands together with the removal of an
   old one, or with the owner's explicit word. Rule budget: one in, one out.

## Action classes

- **Class 0: local and reversible.** Reload a tab, restart a process the owner
  already runs, re-read a file, re-run a local test, click inside a page the
  owner owns when the step is reversible. Act at once, including on a best
  guess: the price of a wrong local step is below the price of an idle system.
  On failure, fix it or record the cause and continue.
- **Class 1: external and cheap, receipt-supervised.** Push to your own branch,
  submit to a designated test chat, deploy to the dev stand, deliver an
  extension update through its own self-update channel. Act, emit the receipt;
  on a recorded failure retry once (see Retries).
- **Class 2: irreversible or foreign-owned.** The invariants' confirmation
  list. Ask the owner one compact question when authority is missing; act on the answer.

Unknown is a state of evidence, not a verdict. An UNKNOWN outcome without a
confirmed turn is a Class 1 failure: it admits exactly one guarded retry. An
UNKNOWN with a confirmed turn is a missing observation: read it
(reconcile_leaf); a confirmed turn is never re-sent. Quota, HumanStop and
permission refusals are not UNKNOWN: they are blocked with a reason and are
never retried automatically.

## Retries

Exactly one guarded retry per UNKNOWN delivery, through the canonical
dispatch_leaf path, under the attempt's original request_id, after a fresh
idle observation of the executor. The retry re-delivers the exact persisted
payload from records/<leaf>/attempts/<key>/handoff.json; it never composes new
bytes, and the brief handoff identity of the attempt never changes. A second
UNKNOWN is final for the attempt: reconcile reads stay allowed, the result stays
UNKNOWN with its recorded cause, and the owner sees that cause directly. A
blocked refusal is not a retry candidate: after confirmed absence of effect a
corrected authorized attempt is a new attempt with linked history.

## Causes

The cause string survives every hop: extension receipt, Herder relay, plan
record, frontier advice. Anything that cannot interpret it must pass it through
verbatim. Closed vocabularies may label causes; they may not gate them.

## Extension and browser delivery

Delivering an extension update is Class 1 through the extension's own
self-update: the runtime compares the on-disk manifest version on a timer and
reloads itself when the disk is newer; the first handshake after a reload
reports the running version as a receipt. Clicking through chrome:// UI is not
a delivery mechanism. Host-managed profiles install through the platform's
managed-extension policy; protected browser state is never edited by hand.
