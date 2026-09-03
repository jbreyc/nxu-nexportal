---
title: "Refer a friend — the reward stated, the code visible, one-tap share, progress"
version: 3
note: "v3 — the brief redefined (second pass: the QR is attributed through the link, not counted as a tap) from the Q3 assessment: value proposition with real amounts; the code always visible; one-tap share per app with pre-filled copy; a QR for in-person sharing; lifetime progress; no eligibility pill."
---
## Outcome

Learners share the referral because the card tells them what they and their friend get, and lets them send it in one tap from the app they already use — or in person, from their screen.

## Users

Active learners in an eligible market, on the dashboard. Two moments: alone, deciding whether to bother; and next to a friend, phone in hand.

## Acceptance criteria

- [ ] THE SYSTEM SHALL state the value proposition in one line at the top of the card, with the amounts the referral service returns for the learner's market: "Give a friend {friend_amount} toward their tuition and earn {learner_amount} toward yours when they enrol."
- [ ] THE SYSTEM SHALL keep the referral code visible on the card at all times, with a copy action beside it — no button to reveal it.
- [ ] THE SYSTEM SHALL render one-tap share buttons for WhatsApp, SMS/iMessage, Telegram and Email, each opening that app with a pre-filled message that carries the value proposition, the code and the link.
- [ ] THE SYSTEM SHALL render a high-contrast QR code beside the code, encoding the referral link, sized to be scanned from a phone screen.
- [ ] THE SYSTEM SHALL render one progress line from the referral service's counts — "{joined} friends joined · {earned} earned" — and append "· {pending} pending" when any referral is pending.
- [ ] WHEN the learner is not in an eligible market, THE SYSTEM SHALL render no card and no eligibility pill.
- [ ] WHEN a share button or the copy action is tapped, THE SYSTEM SHALL emit one `referral_share` event with the channel: whatsapp, sms, telegram, email or copy.
- [ ] THE SYSTEM SHALL encode in the QR the referral link with a `qr` channel parameter, so that an enrolment through it is attributed to the QR by the referral service.

## Design

brief:
Goal: share actions per active learner per month, by channel; referred enrolments per 100 active learners. Baseline the trailing 30 days before release; read two weeks after.
Keep: the card's position on the dashboard (variant B); the code as the identity of the scheme — easy to remember, works on any surface.
Change: the value line with real amounts at the top; the code always visible with a copy action; four one-tap share buttons with pre-filled copy; a QR code beside the code; the progress line under the actions; the "Available in your market" pill removed — eligibility becomes a render condition, documented in the design annotations, not on the component.
Out of scope: the amounts and market eligibility themselves (finance's); the referral landing page and the "How it works" page; a per-referral list; toasts or triggers elsewhere in the product.

## Dependencies

The referral service returns, for the learner's market: eligibility, `friend_amount`, `learner_amount`, currency, the code, the link, and the counts (joined, pending, earned total) — the response is confirmed in refinement; a market without amounts is ineligible. Share deep links need no SDK: `wa.me`, `sms:`, `t.me/share`, `mailto:`. A QR generator in the front end (an existing one, or a small library). The dashboard's event pipeline carries `referral_share`. The referral service attributes an enrolment to the channel parameter on the link it was reached through — confirmed in refinement.

## Out of scope

The amounts and market eligibility rules (finance); the referral landing page; the "How it works" page; a per-referral list or history; toasts or triggers elsewhere in the product; new markets; the referral admin view.

## Size

S — one card: a text line, a visible code with copy, four deep links, a QR, a counts line; no new backend if the referral service already returns the amounts and the counts.

## Requester

@jose (PM), on behalf of learner growth.
