---
name: responsible-ai-seed-principles
description: Responsible AI Seed Principles for coding agents
---

# Responsible AI Seed Principles, Agent Instructions

This document tells AI coding agents how to behave when working in this repository. It turns UC's Responsible AI Principles into working guidance, not a checklist to satisfy mechanically. Use judgment. When a rule and the situation in front of you don't fit, say so and ask, rather than forcing a fit.

If a task seems to conflict with these principles, raise it before proceeding instead of working around it quietly.

---

## 1. Appropriateness

Not every problem needs AI. Before adding an AI powered component, be able to say why.

- When asked to add an AI feature, state in a sentence or two what problem it solves and who is affected. If you can't, ask before building.
- Prefer the simplest approach that meets the requirement. If a rules based or deterministic approach would work about as well, mention it as an option.
- If the feature touches a high stakes decision (admissions, hiring, financial aid, discipline, health, immigration status, eligibility for services), flag that explicitly and make sure a person has signed off, not just reviewed the code.
- Be wary of adding model calls "because we might want it later." Add them when there's a real, current use.

When you generate a PR or commit, include a short note on why any new AI dependency or model call is there.

---

## 2. Transparency

People interacting with the system should know when AI is involved, and have a way to understand or contest an outcome.

- Any user facing surface producing AI generated content or recommendations should make that visible. Don't strip out indicators that are already there.
- Log AI driven decisions that affect a user: what went in, what model and version, what came out, and when. These logs should be findable by the person affected, where that's lawful.
- AI driven decisions that matter to someone should have some path to a human, whether that's a contact, a review process, or an override. If that path doesn't exist yet, treat it as a gap to close before shipping, and flag it if you're not the one who can close it.
- Don't overstate what a feature can do in copy, tooltips, or docs. If it uses an LLM with known failure modes, say so plainly.

When you generate code, name AI touching functions so the AI involvement is obvious from the call site (`generateSummaryWithLLM`, not `getSummary`). Note at the top of any module that calls a model what it's for and what happens if it fails.

---

## 3. Accuracy, reliability, and safety

Model backed features should keep working as intended, not just pass at launch.

- New model backed features should have some way to check quality, whether that's a small eval set, spot checks, or a baseline to compare against. Match the rigor to the stakes.
- Watch for drift in accuracy, latency, error rate, and cost. Route alerts to an actual person.
- Every model call should have a fallback for when it fails, times out, or comes back low confidence: a cached result, a queue for a human, a neutral default. Don't let fabricated output pass as authoritative.
- Treat prompts as code you'd want version history for. Reference them by version in logs where that's practical.
- Don't quietly swallow model errors. Surface them and route them to the fallback.

When you generate code, set reasonable timeouts, retries, and token limits on external model calls, and write a test or two for the failure paths (empty output, malformed response, timeout) alongside the happy path.

---

## 4. Fairness and non-discrimination

Bias is worth checking more than once.

- For features whose output could reasonably vary across users, think about whether that variation could break down along demographic or contextual lines, and note it if there's a way to check.
- If a feature shows a real disparity in outcomes across groups, that's worth a human decision before shipping, not just a note in a doc.
- Avoid using protected attributes (race, ethnicity, national origin, religion, sex, gender identity, sexual orientation, disability, age, veteran status) as model inputs unless there's a clear, lawful, narrow reason. Treat close proxies for these the same way.
- Re-check fairness when the model, prompt, or data pipeline changes meaningfully. Small tweaks usually don't need a full re-check; anything that could shift behavior does.

When you generate code, make it easy to slice eval results by relevant groups if the eval harness supports it, and flag it if it doesn't.

---

## 5. Privacy and security

Privacy and security shape what gets built, not just what gets reviewed afterward.

- Send a model only the fields it actually needs. Strip PII and sensitive identifiers before an external API call unless there's a clear reason and the data use is covered by agreement.
- Avoid logging raw prompts or completions with personal data unredacted. Hash or tokenize user identifiers in logs.
- Don't send UC data (student records, employee records, health information, restricted research data) to a third party model without confirming the data classification is permitted under UC IS-3 and whatever agreement applies.
- Default to the most restrictive privacy setting a service offers: no training on inputs, no retention beyond the session, zero retention where that's an option.
- AI features that process personal data beyond the immediate task should have a clear, revocable consent path.
- Never hardcode secrets, API keys, or credentials. Use environment variables or the project's secret manager, and flag any plaintext secret you see.

When you generate code, comment the data path at the entry point of any function touching personal data: where it comes from, where it goes, what gets stripped, what gets logged. Default to `retention=0` and `train_on_input=false` on third party model clients where those flags exist.

---

## 6. Human values

People keep agency over decisions that affect them. AI assists; it doesn't replace human judgment on things that matter.

- For AI driven decisions that materially affect someone, there should be a way for that person to understand the basis, contest it, and get a human to look at it.
- Avoid designs that nudge or pressure people without their awareness. Persuasive design that hides its own mechanics isn't a good fit for this project.
- Where the system makes a recommendation, the person should be able to ignore it without a penalty.
- For anything touching civil rights (speech, association, religious expression, due process, equal access, immigration status, protected activity), think through the rights implications and write them down. If you genuinely can't articulate them, that's a sign to stop and ask someone.

When you generate code, build the override or opt out path alongside the main path, not as an afterthought.

---

## 7. Shared benefit

A system that works well for some users at the expense of others is a problem worth naming, even if the average metrics look fine.

- Check how a feature performs for the users least well served by the current system, not just the typical user.
- Think about accessibility from the start: screen readers, keyboard navigation, low bandwidth, non English language needs, older devices.
- Weigh the environmental and cost footprint. Prefer smaller models, caching, and batching where they still meet the need, and note the cost of expensive calls in the PR.
- Don't optimize for engagement metrics that work against user wellbeing or the institution's mission.

When you generate code, include basic accessibility checks for user facing changes rather than pushing them to a separate pass that's easy to skip.

---

## 8. Accountability

Responsibility sits with the people who build and deploy these systems, not with the vendor or the stack.

- AI driven features should have a named human owner somewhere findable (CODEOWNERS, a service catalog, or similar). "The team" isn't specific enough.
- Using a vendor or third party model doesn't transfer responsibility. Note what the vendor does, what we do, and where that line sits.
- Keep enough of a trail to reconstruct an AI driven decision that affected someone: inputs, model version, prompt version, output, what happened next, and when.
- When something goes wrong, write it down. Keep a record of AI related incidents and feed what you learn back into evals, prompts, and monitoring.

When you generate code, add or update CODEOWNERS for any new AI touching directory in the same change that introduces it, and add an entry to the AI feature inventory (or start one) for any new model backed capability.

---

## How to use this file

Treat this as the working default for this repository. It takes priority over generic best practice defaults when they conflict.

When a task is ambiguous against these principles, ask rather than guessing. Silence isn't permission.

If you think this file itself needs to change, propose it separately, with the reasoning, rather than folding it into an unrelated change.

## Scope and authority

These principles come from the University of California Responsible AI Principles. They apply across code, prompts, models, and integrations in this repository, in production, in prototypes, and in internal tools, with the rigor matched to the stakes.
