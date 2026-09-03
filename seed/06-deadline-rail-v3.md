---
title: "Deadline rail — the next four dated items across coursework, payments, documents, registration"
version: 3
note: "v3 after the second needs-info: coursework never reads 'overdue' without a grade (no submission signal exists and none is used); registration carries the adds-close date and is dropped, never overdue."
---
## Outcome

Learners see the next four dated items — coursework, payments, documents, registration — at the top of the dashboard, nearest first, so nothing with a date is discovered after it has passed.

## Users

All active learners, every dashboard load. The rail is the first component above the fold in the new dashboard layout, which ships to every learner — there is no experiment.

## Acceptance criteria

- [ ] THE SYSTEM SHALL build the rail from the dated events the dashboard receives today, one rule per category: coursework — `assignment due` gives the date and `grade posted` for that assignment resolves it, and no submission signal is used; payments — `invoice issued` gives the due date from its payload and `invoice paid` resolves it; documents — `document status changed` to `requested` gives the deadline from its payload and a change to `received` or `verified` resolves it; registration — `registration window opened` creates one item carrying the adds-close date (day 5 of term) from its payload, resolved when the learner's course count reaches two or the adds-close date passes.
- [ ] THE SYSTEM SHALL render the four nearest unresolved items by date ascending, each with its category label, its title and the days remaining.
- [ ] WHEN a coursework item's due date has passed and no grade is posted, THE SYSTEM SHALL keep it in the rail labelled "awaiting grade" — never "overdue" — until the grade is posted.
- [ ] WHEN a payments or documents item's date has passed and it is unresolved, THE SYSTEM SHALL keep it in the rail, pinned first, labelled "overdue" with the days elapsed, until it is resolved.
- [ ] WHEN the adds-close date passes and the learner has fewer than two courses, THE SYSTEM SHALL drop the registration item with no overdue state.
- [ ] WHEN an item is due within 2 days, THE SYSTEM SHALL render its days-remaining label in the alert colour named in the design frame; within 7 days, the warning colour; otherwise the default text colour.
- [ ] WHEN the learner taps an item, THE SYSTEM SHALL open that item's own surface: Canvas for coursework, the wallet for payments, the documents page for documents, course selection for registration.
- [ ] WHEN fewer than four unresolved items exist, THE SYSTEM SHALL render only those that exist and no empty rows; WHEN none exist, THE SYSTEM SHALL render the rail with the single line "Nothing due — you're clear."
- [ ] WHEN a resolving event arrives, THE SYSTEM SHALL drop the item from the rail on the next dashboard load.

## Design

https://www.figma.com/file/nexportal/deadline-rail-v2 — the frame names the alert and warning colours, the overdue treatment and the "awaiting grade" treatment.

## Dependencies

The payloads of `invoice issued` (due date), `document status changed` (deadline) and `registration window opened` (adds-close date) carry those dates — assumed; engineering confirms before build, and a category whose payload lacks its date ships without that category, size unchanged. No Canvas submission signal is needed or used. The design frame at 360px and 1280px widths.

## Out of scope

Push notifications or email; a "see all deadlines" page beyond the existing one; changes to how Canvas due dates or the invoice provider's due dates reach myNXU; a submission signal from Canvas; any experiment or bucketing — the layout ships to all learners.

## Size

S — one component over events the dashboard already receives; the per-category resolve rules, the colour thresholds and the four routes are the whole logic.

## Requester

@jose (PM)
