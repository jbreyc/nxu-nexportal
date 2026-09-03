---
id: "01"
entry: gate
title: "Refer a friend — link first, the exchange stated, referral state"
requester: jose
weekday: Tuesday
---
## Outcome

Learners with no distribution channel share the referral at least once: the card gives them a reason and a one-tap way to send it.

## Users

Active learners in an eligible market, on the dashboard — and at the two moments that produce the impulse to share: a course grade posted, a credential earned.

## Acceptance criteria

- [ ] WHEN the learner is in an eligible market, THE SYSTEM SHALL render the card with a share link as the primary action and the code as a secondary "prefer a code?" action.
- [ ] THE SYSTEM SHALL state, in one line above the action, what the friend gets, what the learner gets, where it lands (the wallet) and when.
- [ ] WHEN a referral changes state, THE SYSTEM SHALL show it on the card as invited / started / credited, with the credited amount.
- [ ] WHEN a course grade is posted or a credential is earned, THE SYSTEM SHALL show the card as a toast with the same copy and the same single action.
- [ ] WHEN the learner is not in an eligible market, THE SYSTEM SHALL render nothing — no card, no eligibility pill.

## Design

brief:
Goal: share taps per active learner per month; referred starts per 100 active learners. Measured in-sprint from the link's UTM and the referral service's state changes.
Keep: the card's position on the dashboard (variant B); the market-eligibility logic, moved from a visible pill to a render condition.
Change: the share link becomes the primary action and the code a secondary "prefer a code?" link; one line above the action states the exchange (what the friend gets, what you get, credited to your wallet when they start); a referral-state line lists invited / started / credited with amounts; the same card appears as a toast at grade-posted and credential-earned — one action, dismissable.
Out of scope: incentive amounts, new markets, referral admin, the "How it works" page.

## Dependencies

The referral service exposes per-referral state (invited / started / credited) and the credited amount. The wallet credit event is observable to the dashboard. Grade-posted and credential-earned events already exist in myNXU (they drive the deadline rail today).

## Out of scope

Incentive amounts; opening new markets; the referral admin view; changes to the "How it works" page; any change to the code-based flow beyond demoting it.

## Size

S — one card, two states, one toast; no new backend beyond reading referral state that already exists.

## Requester

@jose (PM), on behalf of learner growth.
