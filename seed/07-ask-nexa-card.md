---
title: "Ask Nexa — programme, payment and deadline questions from the learner's own record"
status: In Sprint
requester: support
size: M
---
## Outcome

A learner asks a programme, payment or deadline question on the dashboard and gets an answer grounded in the catalogue and their own record, with a one-tap handoff to a person when Nexa cannot answer.

## Users

Active learners, on the dashboard, at the moment a question blocks them — most often "when does my tuition need to be paid?" and "what happens if I miss Friday?".

## Acceptance criteria

- [ ] WHEN the learner submits a question, THE SYSTEM SHALL answer from the catalogue and the learner's record within 5 seconds, naming the record field it used (invoice, deadline, standing).
- [ ] WHEN Nexa cannot answer, THE SYSTEM SHALL say so and offer "Talk to a person", which opens a support ticket pre-filled with the question and the learner's context.
- [ ] THE SYSTEM SHALL never state a grade, standing or payment status that is not in the learner's own record.

## Design

https://www.figma.com/file/nexportal/ask-nexa-card

## Dependencies

Nexa's answer API with learner-record access; the support ticket system's create endpoint; the catalogue index Nexa reads today.

## Out of scope

Proactive nudges; answering about other learners; changes to Nexa's model or catalogue.

## Size

M — a card, a conversation view, and the handoff; Nexa itself exists.

## Requester

@support (Learner Support)
