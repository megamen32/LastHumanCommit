---
name: user-testing
description: Independently attempt a user goal through a real browser, device, application or CLI, returning observable usability and behavior evidence without reading implementation.
---

# Real-use testing

Used by the mandatory single Full Tester and as a standalone capability. It is
not source review. Receive a goal, relevant persona/conditions, intended result,
product revision, real surface and suitable test account/data. A recipe of exact
clicks is appropriate for a regression replay, not for discovering whether a user
can find their own way.

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
recovery attempt and useful evidence. Classify a proven defect, usability obstacle,
personal preference or unverified concern; blunt criticism is welcome but needs
an observed episode. Do not convert every preference into a feature requirement.

Return PASS, CHANGES_REQUIRED or BLOCKED_REAL_SURFACE. For repairs, replay the
original failure and make a fresh uninstructed attempt when discoverability matters.
Source-informed diagnosis and implementation belong to Worker, not the Tester.
