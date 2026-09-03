---
title: "Deadline rail — the next four dated items across coursework, payments, documents, registration"
version: 2
note: "v2 after the gate's needs-info on #6: the date and the resolving event per category, overdue behaviour, registration shows the close, no experiment."
---
## Outcome

Learners see the next four dated items — coursework, payments, documents, registration — at the top of the dashboard, nearest first, so nothing with a date is discovered after it has passed.

## Users

All active learners, every dashboard load. The rail is the first component above the fold in the new dashboard layout, which ships to every learner — there is no experiment.

## Acceptance criteria

- [ ] THE SYSTEM SHALL build the rail from the dated events the dashboard receives today, using for each category the date and the resolving event named here: coursework — `assignment due` (date: the due date; resolved by `grade posted` for that assignment); payments — `invoice issued` (date: the due date in the invoice payload; resolved by `invoice paid`); documents — `document status changed` to `requested` (date: the deadline in the payload; resolved by a change to `received` or `verified`); registration — `registration window opened` (date: the window's close date, "adds close", in the payload; shown from open to close; resolved by the window closing or a course selection).
- [ ] THE SYSTEM SHALL render the four nearest unresolved items by date ascending, each with its category label, its title, and the days remaining.
- [ ] WHEN an item's date has passed and it is unresolved, THE SYSTEM SHALL keep it in the rail, pinned first, labelled "overdue" with the days elapsed, until it is resolved.
- [ ] WHEN an item is due within 2 days, THE SYSTEM SHALL render its days-remaining label in the alert colour named in the design frame; within 7 days, the warning colour; otherwise the default text colour.
- [ ] WHEN the learner taps an item, THE SYSTEM SHALL open that item's own surface: Canvas for coursework, the wallet for payments, the documents page for documents, course selection for registration.
- [ ] WHEN fewer than four unresolved items exist, THE SYSTEM SHALL render only those that exist and no empty rows; WHEN none exist, THE SYSTEM SHALL render the rail with the single line "Nothing due — you're clear."
- [ ] WHEN a resolving event arrives, THE SYSTEM SHALL drop the item from the rail on the next dashboard load.

## Design

https://www.figma.com/file/nexportal/deadline-rail-v2 — the frame names the alert and warning colours and the overdue treatment.

## Dependencies

The event payloads named in the first criterion carry the dates and the resolution signals — assumed; engineering confirms which do before build, and a category whose payload lacks the date ships without that category, size unchanged. The design frame at 360px and 1280px widths.

## Out of scope

Push notifications or email; a "see all deadlines" page beyond the existing one; changes to how Canvas due dates or the invoice provider's due dates reach myNXU; any experiment or bucketing — the layout ships to all learners.

## Size

S — one component over events the dashboard already receives; the overdue rule, the colour thresholds and the four routes are the whole logic.

## Requester

@jose (PM)
