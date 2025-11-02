# Analysis and recommendations

## Innovative use cases

1. **Autonomous break triage** – The LLM annotator classifies severity, proposes next best actions and identifies breaks suitable for bots vs. humans.
2. **Custody outreach drafting** – Use the agent plan payload to auto-draft SWIFT MT565/566 messages or custodial emails, with human approval for escalated cases.
3. **Ledger ingestion watchdog** – Trigger NBIM booking retries or data lake refreshes automatically for "MISSING_IN_NBIM" breaks with high confidence.
4. **Scenario rehearsal** – Generate synthetic dividend events via LLMs to stress test reconciliation tolerances and train operators.

## Safeguards & risk mitigation

- **Model spend control** – Cache annotations per `coac_event_key` and cap daily API calls. Fall back to deterministic messaging if spending approaches the $15 budget.
- **Guardrailed outputs** – Enforce JSON schema responses (implemented) and validate severity against allow-lists to prevent prompt injection side effects.
- **Access control** – Store API keys in vault solutions (Azure Key Vault, Hashicorp Vault) and scope IAM roles to reconciliation services only.
- **Dual controls** – Require human approval for tasks marked `needs_escalation = True` or severity `HIGH`/`CRITICAL` before enacting remediation.
- **Monitoring** – Log raw LLM payloads (`raw_annotation`) for audit, and feed resolution outcomes back into evaluation dashboards.

## Practical next steps

1. Integrate the agent plan with NBIM's workflow queue (ServiceNow, JIRA) to dispatch tasks to humans or bots.
2. Build the specialist agents incrementally, starting with a custody outreach assistant that drafts responses based on the plan payload.
3. Instrument success metrics (time-to-resolve, false positives) and use them to tune tolerance rules and prompts.
4. Extend the dataset to full production scale and parallelise LLM calls using async batching while respecting spend guardrails.
