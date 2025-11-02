# Analysis & Recommendations

## Observations from Test Data
1. **Late custodian booking (coac_event_key 1001)** – NBIM shows a settled dividend while the custodian feed is empty. High severity; likely requires custodian escalation and position validation.
2. **Currency mismatch (coac_event_key 1002)** – Same ISIN/account but divergent currency codes, indicating static-data misalignment. Medium severity with opportunity for automated static-data checks.
3. **Amount variance (coac_event_key 1003)** – Difference exceeds tolerance after FX conversion; probable tax or rate source discrepancy. Medium severity and a good candidate for rate-source reconciliation playbooks.

## Innovative Extensions
- **Playbook drafting:** Use the LLM to draft ServiceNow ticket descriptions, attaching relevant records and suggesting assignee groups automatically.
- **Scenario simulation:** Ask the model to stress-test breaks under different FX/tax scenarios before traders arrive, prioritising by potential cash exposure.
- **Agentic retrieval:** Augment prompts with embeddings over historical reconciliations so the assistant can cite past resolutions and estimated timelines.
- **Guarded auto-remediation:** When automation mode returns `autopilot` with confidence >0.8, automatically stage adjusting journal entries for dual approval.

## Risk & Mitigation
| Risk | Mitigation |
| --- | --- |
| Over-reliance on model output | Deterministic checks remain primary; LLM only annotates after rules fire. Confidence + automation flags require human acknowledgement for high-impact actions. |
| Cost overruns | Cached responses keyed by reason + context; summariser runs once per batch. Monitor token usage per run and cap via environment variables. |
| Data leakage | Only minimal transaction attributes sent to API. Optionally route through Azure OpenAI in-region; redact client names before prompts. |
| Model drift | Version prompts and capture responses in artefacts. Schedule periodic human review and regression tests using stored transcripts. |

## Next Steps
1. Integrate a lightweight vector store (e.g., SQLite + embeddings) to recall prior break resolutions.
2. Expose a REST API that operations dashboards can call for live reconciliation status.
3. Pilot auto-drafting of remediation tickets with human-in-the-loop approval before execution.
4. Expand test harness with synthetic edge cases to benchmark LLM guidance quality quarterly.
