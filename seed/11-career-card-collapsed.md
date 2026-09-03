---
title: "Career card — collapsed by default once a phase is complete; the choice remembered"
note: "The recording's answered body (second take): the request goes through intake and draft, then this body replaces the draft."
---
## Outcome

Learners past their first career phase land on their deadlines and progress, not on a hero they have seen a hundred times: the career card starts collapsed for them, and their choice to expand it is remembered.

## Users

Active learners with at least one completed career phase, every dashboard load. Learners in their first phase keep the expanded card.

## Acceptance criteria

- [ ] WHEN the learner has completed at least one career phase, THE SYSTEM SHALL render the career card collapsed on dashboard load: one line with the career goal, the current phase name and an "Expand" control.
- [ ] WHEN the learner has completed no career phase, THE SYSTEM SHALL render the career card expanded, as today.
- [ ] WHEN the learner taps "Expand" or "Collapse", THE SYSTEM SHALL store the choice in the learner's dashboard preferences and apply it on every later load, overriding the phase rule.
- [ ] THE SYSTEM SHALL render the collapsed card at the height of one text line plus the card padding named in the design frame, and never taller.
- [ ] WHEN the card is collapsed, THE SYSTEM SHALL show no other hero content; "View my learning path" stays inside the expanded state.

## Design

https://www.figma.com/file/nexportal/career-card-collapsed

## Dependencies

Career phases and their completion, already rendered on the card; the learner's dashboard preferences, where the card's collapse control stores its state today; the design frame for the collapsed line at 360px and 1280px.

## Out of scope

Changing the phase logic or the hero copy; the percentage pill (removed separately); animating the transition; any change for learners in their first phase.

## Size

S — a default rule and a stored preference on an existing collapse control.

## Requester

@learner-success
