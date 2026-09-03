---
title: "Course load card — days until adds close, for the first five days of term"
note: "The recording's answered body: the request goes through intake and draft, then this body replaces the draft."
---
## Outcome

A learner in the first five days of a term sees on the course-load card how many days remain to add a second course, so the add window is never discovered after it closes.

## Users

Active learners with one course selected and room for a second, on the dashboard, during days 1–5 of the term.

## Acceptance criteria

- [ ] WHEN the term is in days 1–5 and the learner has fewer than two courses, THE SYSTEM SHALL render "Adds close in N days" on the course-load card, where N counts down from the term's adds-close date.
- [ ] WHEN the learner's CGPA is below 3.00, THE SYSTEM SHALL render the countdown with the sentence "A second course needs a CGPA of 3.00" instead of the "Add a course" link.
- [ ] WHEN the adds-close date has passed or the learner already has two courses, THE SYSTEM SHALL render nothing extra on the card.
- [ ] WHEN the learner taps "Add a course", THE SYSTEM SHALL open course selection, as the existing link does today.

## Design

https://www.figma.com/file/nexportal/course-load-adds-close

## Dependencies

The term's adds-close date (day 5 of term) and the learner's CGPA and course count, all already on the course-load card; the design frame for the one extra line.

## Out of scope

Changing the adds-close rule or the CGPA gate; notifications; the seminar slot.

## Size

S — one conditional line on an existing card, from data the card already renders.

## Requester

@registrar
