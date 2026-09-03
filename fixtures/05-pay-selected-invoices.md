---
id: "05"
entry: gate
title: "Wallet — pay selected invoices"
requester: finance-ops
weekday: Wednesday
---
## Outcome

A learner with more than one open invoice pays the ones they choose, in one action, and sees the total update before paying.

## Users

Learners with two or more open invoices on the wallet card — typically a current-term instalment plus a next-term instalment.

## Acceptance criteria

- [ ] WHEN the wallet card lists two or more open invoices, THE SYSTEM SHALL show a checkbox per invoice, with the earliest-due invoice checked by default.
- [ ] WHEN the learner changes the selection, THE SYSTEM SHALL update the "Pay selected" amount to the sum of the checked invoices before any payment starts.
- [ ] WHEN the learner taps "Pay selected", THE SYSTEM SHALL take them to checkout for exactly the checked invoices.
- [ ] WHEN a payment succeeds, THE SYSTEM SHALL mark the paid invoices as paid on the card within 60 seconds and leave the others open.
- [ ] WHEN no invoice is checked, THE SYSTEM SHALL disable "Pay selected".

## Design

https://www.figma.com/file/nexportal/wallet-pay-selected

## Dependencies

The wallet card (variant B) already lists open invoices with due dates. The checkout page accepts an amount.

## Out of scope

Payment plans, refunds, currency changes, invoice disputes, the "All invoices" page.

## Size

S — a selection state on an existing card and a checkout link that carries the selection.

## Requester

@finance-ops (Finance)
