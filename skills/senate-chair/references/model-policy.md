# On-Prem Model Policy

This skill handles Senate Chair correspondence, cases, and scheduling, so it runs only on models hosted on UCSD-controlled infrastructure. Do not use it with commercial cloud models.

## Approved models

- `api-glm-5.3`

Confirm and extend this list with the TritonAI team before adding any other model. If the list is empty or unclear, treat the skill as unavailable and ask the Chair to confirm the approved models.

## Enforcement

1. Before any task, check the session's selected model against this list.
2. If the selected model matches, proceed.
3. If it does not match, stop. Do not read mail, files, calendar, or case content. Tell the Chair: "This skill is limited to UCSD on-prem models. Switch to an approved model and try again."
4. If the selected model cannot be verified, say so and stop.

## Data boundary

- Mail, calendar, case, and answer-bank content stays within the approved on-prem model session.
- Do not send Chair content to any other model, service, or endpoint.
