---
title: "Deadline rail — the next four dated items across coursework, payments, documents, registration"
status: Ready
requester: jose
size: S
---
## Outcome

Learners see the next four dated items — coursework, payments, documents, registration — at the top of the dashboard, nearest first, so nothing with a date is discovered late.

## Users

All active learners, every dashboard load; the rail is the first thing above the fold on variant B.

## Acceptance criteria

- [ ] THE SYSTEM SHALL render the four nearest dated items from the events already available to the dashboard (assignment due, invoice due, document expiry, registration window opens), ordered by date ascending, each with its category label and days remaining.
- [ ] WHEN an item is due within 2 days, THE SYSTEM SHALL render its days-remaining label in the alert colour from the design frame; within 7 days in the warning colour; otherwise in the default text colour.
- [ ] WHEN the learner taps an item, THE SYSTEM SHALL open the item's own surface: Canvas for coursework, the wallet for payments, the documents page for documents, course selection for registration.
- [ ] WHEN fewer than four dated items exist, THE SYSTEM SHALL render only those that exist and no empty rows.
- [ ] WHEN an item's underlying event is resolved (submitted, paid, uploaded, selected), THE SYSTEM SHALL drop it from the rail on the next dashboard load.

## Design

https://www.figma.com/file/nexportal/deadline-rail-v2

## Dependencies

The events already reaching the dashboard: assignment due (from Canvas), invoice issued/paid, document status changed, registration window opened. The design frame at 360px and 1280px widths, with the alert and warning colours named.

## Out of scope

Push notifications or email for deadlines; a "see all deadlines" page beyond the existing one; changes to how Canvas due dates are synced.

## Size

S — one component over events the dashboard already receives; the colour thresholds and the four routes are the whole logic.

## Requester

@jose (PM)
