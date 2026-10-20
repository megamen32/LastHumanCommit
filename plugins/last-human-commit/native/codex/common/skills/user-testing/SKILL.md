---
name: user-testing
description: Independently attempt a user goal through a real browser, device, application or CLI, returning observable usability and behavior evidence without reading implementation.
---

# Real-use testing

Load `<primary checkout>/.agents/TEST_ACCESS.md` via Git worktree mapping before
acceptance; follow `common/protocols/REVIEW_TO_DELIVERY.md` execution-access contract.
Reuse/recover authorized fixtures through supported local administration before classifying a missing login as BLOCKED_REAL_SURFACE.
Initial password change and authorized disposable OAuth registration are preparation,
not blanket blockers. Keep protected references, never values, in context/handoffs.
Do not use admin as ordinary QA or exceed direct limits. Completed assigned coverage
needs no recursive testing; product defects and parent acceptance remain separate.

Run at a major milestone and its final acceptance, roughly 3 hours of coherent
work, not every hour, tool call or small edit. The boundary is a usable outcome,
not an arbitrary elapsed deadline; do not wait three hours for a ready milestone
or split a substantial outcome into fragments to evade independent testing.
Technical tests continue throughout development.

Before code, define a tangible outcome: who is solving which real task, the
before/after difference and a real entry point. For a bug start TDD immediately:
reproduce the failing behavior RED, repair it GREEN, then check the original
scenario. An internal refactor, dependency or SHA is a means toward an observable
user/consumer outcome, not a substitute for it. API and CLI consumers count too.

This is user testing, not source review. Receive a plausible persona, a realistic
goal and relevant conditions, the real surface and allowed test data. Receive
no implementation history and not the expected verdict, changed control names,
a success click recipe or other testers' findings. Source-informed regression
replay is a different, explicitly labelled check.

Start fresh, without source code, implementation chats or internal explanations.
In normal use, public help available to a real user is allowed. In a separately
labelled first-contact/discoverability experiment, begin without hints. Do not
confuse these experiments or pretend an experienced agent has no prior knowledge.

Actually perform actions with the working surface tool: browser automation or
computer use for web, Agent Device where available for mobile/native devices,
the real application for desktop, or a real shell invocation for CLI. Check actual
resulting state. A screenshot, successful tool invocation or green process health
is not alone proof of the user's goal. Record a tool/environment failure separately.

Use designated test identities and data. Exercise meaningful writes when the task
and environment allow them. Messaging/payment/invitation flows should use the
established test destination or sandbox, not unrelated real people or accounts.
A missing login/surface is BLOCKED_REAL_SURFACE, not simulated success.

On a browser error, timeout or ambiguous state, capture and inspect a secret-safe
screenshot in the owning session before retry, navigation or cleanup. If capture
is unavailable, record the missing evidence and tool limitation.

Capture goal, actions tried, expected versus observed result, failure point,
recovery attempt and useful evidence. Explain what helped, what confused you,
what you liked/disliked, where you hesitated and whether the result solves your
actual task. Preserve detailed candid feedback rather than compressing it into
PASS/FAIL or only critical bugs. An honest "nothing notable" is better than
invented praise or criticism; useful detail has no arbitrary short word quota.
Classify a proven defect, usability obstacle, preference or unverified concern;
blunt criticism needs an observed episode. Do not turn every preference into a
mandatory feature, and do not throw preferences away before Lead has read them.

When both before/after versions are safe and available, a neutral comparison can
show whether the tester independently notices the practical difference. Do not
reveal which version is expected to win or replay harmful production defects.
Otherwise prove the new behavior and retain the failing baseline/TDD separately;
a tester who never saw the old version must not claim an observed comparison.

Return PASS, CHANGES_REQUIRED or BLOCKED_REAL_SURFACE. For repairs, replay the
original failure and make a fresh uninstructed attempt when discoverability matters.
Source-informed diagnosis and implementation belong to Worker, not the Tester.
