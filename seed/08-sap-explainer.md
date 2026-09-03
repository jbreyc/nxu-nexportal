---
title: "SAP card — standing is the weakest of three; say which"
status: Done
requester: registrar
size: S
---
## Outcome

Learners understand why their standing is what it is: the SAP card names the weakest of CGPA, pace and time used, and what would change it.

## Users

All learners; above all those in warning or probation.

## Acceptance criteria

- [ ] THE SYSTEM SHALL render the three measures with their thresholds (CGPA minimum 2.00, pace minimum 67%, maximum time frame) and mark the weakest as the one that sets the standing.
- [ ] WHEN standing is warning or probation, THE SYSTEM SHALL render one sentence naming the measure to improve and the "Raise a request" link.

## Design

https://www.figma.com/file/nexportal/sap-card

## Dependencies

SAP standing as computed by the registrar service (already on the card).

## Out of scope

Changing SAP rules; appeals; notifications.

## Size

S — copy and one highlight rule on an existing card.

## Requester

@registrar
