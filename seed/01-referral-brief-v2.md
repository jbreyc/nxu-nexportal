---
title: "Refer a friend — link first, the exchange stated, referral state"
version: 2
note: "v2 of fixture 01 after the gate's needs-info: toast rules, amounts source, one-tap semantics, N-referral layout, delivery."
---
## Outcome

Learners with no distribution channel share the referral at least once: the card gives them a reason and a one-tap way to send it.

## Users

Active learners in an eligible market (the referral service returns amounts for their market), on the dashboard — and at the two moments that produce the impulse to share: a course final grade posted, a credential earned.

## Acceptance criteria

- [ ] WHEN the referral service returns amounts for the learner's market, THE SYSTEM SHALL render the card with one primary "Share" action and a secondary "prefer a code?" link that reveals the code.
- [ ] WHEN the learner taps "Share" on a browser with the Web Share API, THE SYSTEM SHALL open the native share sheet with the link; otherwise THE SYSTEM SHALL copy the link and show "Copied" for 3 seconds. Both emit one `referral_share_tap` event with `method` = `share_sheet` or `copy`.
- [ ] THE SYSTEM SHALL render, in one line above the action, the friend amount, the learner amount and the currency from the referral service's response, in the form "They get {friend}, you get {learner} in your wallet when they start their first course."
- [ ] THE SYSTEM SHALL render one referral-state line with aggregate counts and the credited total — "3 invited · 1 started · 1 credited ({total})" — from the referral service's state counts; no per-referral list on the card.
- [ ] WHEN a course final grade is posted or a credential is earned, THE SYSTEM SHALL show the card as a dismissable toast on the learner's next dashboard load, at most one referral toast per learner per 7 days; a dismissed toast is not shown again for that event.
- [ ] WHEN the referral service returns no amounts for the learner's market, THE SYSTEM SHALL render neither the card nor the toast, and no eligibility pill.

## Design

brief:
Goal: `referral_share_tap` per active learner per month, and referred starts per 100 active learners; baseline the trailing 30 days before release, read two weeks after.
Keep: the card's position on the dashboard (variant B); the card's height — the state line is one line of counts, never a list.
Change: "Share" primary (share sheet where supported, copy-with-"Copied" elsewhere), the code demoted to a "prefer a code?" link; the exchange line with the market's amounts and the word wallet; the counts line; the toast variant — same copy, same single action, a dismiss control — for the two moments above.
Out of scope: incentive amounts and market eligibility (finance's), a per-referral list, the "How it works" page, live push of the toast.

## Dependencies

Referral service: the eligibility response carries `friend_amount`, `learner_amount`, `currency` for the learner's market, and the state counts (invited / started / credited, credited total) — confirmed in refinement before build; if amounts are absent the card renders nothing. "Started" = the referred learner's first course day, the moment the credit lands. Events: course final grade posted and credential earned already reach the dashboard (they drive the deadline rail); the toast reads them on dashboard load and stores its dismissed / last-shown state in the learner's dashboard preferences, where card collapse state lives today. Analytics: the dashboard's existing event pipeline carries `referral_share_tap`; if there is none, instrumentation is the first task of the sprint and the goal is read from the referral service's counts alone.

## Out of scope

Incentive amounts and market eligibility rules (finance); a per-referral list or history; the "How it works" page; live (in-session) delivery of the toast; new markets; the referral admin view.

## Size

M — one card with three states, a share-method switch, and a toast on load; no new backend if the referral service already returns market amounts and state counts (confirmed in refinement; if not, L).

## Requester

@jose (PM), on behalf of learner growth.
