---
name: focus-groups
description: Run a focus group (фокус-группа) of Zero Knowledge testers on the real product - diverse personas on mobile and desktop pursue their own goals through a browser, report what they like and do not, are asked what each button does, and every finding is fixed, redeployed and retested in rounds without waiting.
---

# Focus groups

A focus group is several fresh Testers (`src/common/agents/Tester.md`) imitating
real people. They never see code, diffs or reports; they use the deployed
product only through a browser (Agent Browser or another browser MCP), a device
or the real CLI. L runs it to completion without asking the owner, at a ready
milestone or on the owner's request; it is not a mandatory schedule (not every
hour or edit).

## Prepare (yourself, never a blocker)

- Deploy the candidate to the dev environment (`.agents/PROJECT.md` `dev`, or
  `TEST_ACCESS.md`).
- Create what testers need: register new accounts, demo cabinets, test data and
  credentials through the product's normal sign-up or its admin tools; hand
  them over as protected references; delete them afterwards. Access rules:
  `.agents/TEST_ACCESS.md` and the active package's
  `common/protocols/REVIEW_TO_DELIVERY.md`.
- Check model quotas (`model-availability`) and spread testers over the allowed
  tiers for diversity.

## Form the group

Three testers in parallel per group by default. Each gets a persona: name, age,
profession, experience (from complete novice to power user), personality
(impatient, methodical, exploratory), device (part on mobile, part on desktop),
and their own realistic goal on the changed part of the product. Use random
variation within the real audience, not only users likely to succeed. No
solution path, no names of changed controls. Do not stereotype: never tie
competence to age or any demographic trait.

## Each tester

1. Pursues their goal like an ordinary user, on a fixed product revision, and
   touches everything they can except destructive actions; never sends anything
   to real external people (test chats are fine).
2. Reports freely: what they liked, what they did not, what was clear and what
   was not, where they got stuck, whether they reached the goal, with screenshots
   of decisive moments.
3. After finishing, L (or the tester's own follow-up turn) asks them about every
   button and control they saw: "what do you think this does?". Mismatches with
   real behavior are findings.

Keep each tester's raw feedback, positive and negative; do not reduce it to
PASS/FAIL. Ask for concrete episodes, but this is not a word quota or a demand
to manufacture criticism.

L also looks with its own eyes: opens the screenshots, and for a UI with themes
checks both light and dark, on a phone-sized and a desktop viewport. Unreadable
text, white tiles on dark, broken scroll or a layout that is not native-feeling on
mobile are findings even if no tester mentioned them.

## Fix and repeat

- As soon as a group's feedback arrives, L sorts it: real obstacles first,
  preferences recorded (they do not become scope by themselves). Product
  direction from the owner wins: easy for novices, configurable for power users
  without getting in the novices' way (an "advanced" mode is a typical answer).
- Assign each fix to a Worker (frontier tier for UX work) immediately, merge it,
  redeploy, and start the next group on the new revision. Nobody waits for the
  owner.
- Groups run one after another; testers inside a group run in parallel. A new
  group gets fresh personas and is not told what changed.
- Stop when the testers' goals succeed, serious obstacles are gone and a new
  round brings only minor preferences, or after the round limit the owner set.

## Result for the owner

In their language: rounds run, personas and devices, what was fixed, what testers
liked, open issues, links to raw feedback and screenshots. Simulated personas are
not actual customers and not market evidence.
