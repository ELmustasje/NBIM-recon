# LLM-Powered Reconciliation Architecture Vision

## 1. Mission Control Overview
- **Data ingestion layer** normalises NBIM and custodian files into `DividendRecord` objects and logs provenance for audit.
- **Deterministic guardrails** (matching + rule checks) continue to anchor the workflow, ensuring that high-confidence breaks are detected without model hallucination.
- **LLM Intelligence Fabric** augments each break with narrative, remediation, and automation metadata through the `BreakAdvisor` service.
- **Knowledge surfaces** expose actionable artefacts (CSV, JSON, Markdown briefs) that downstream operators and tooling can consume.

## 2. Agent Constellation
| Agent | Responsibility | Safeguards |
| --- | --- | --- |
| **Break Classifier** (`BreakAdvisor.annotate_break`) | Consumes deterministic reason codes + record context, calibrates severity, synthesises explanations, proposes remediation and automation mode. | Structured JSON schema, deterministic fallback library, confidence score, API timeouts. |
| **Ops Chief of Staff** (`BreakAdvisor.summarize_breaks`) | Produces triage-ready brief: ordering by urgency, risk commentary, automation opportunities, and escalation matrix. | Triggered only after guardrail checks succeed, can be versioned for audit, disabled when API unavailable. |
| **Scenario Simulator** *(future)* | Queries historical knowledge base for similar breaks to pre-fill remediation runbooks and calculate expected financial exposure. | Offline mode with synthetic data, manual approval gates before posting adjustments. |
| **Auto-Remediator** *(future)* | Executes low-risk adjustments (e.g., status alignments) through ticketing or booking APIs once confidence and automation mode meet thresholds. | Requires two-person approval, integrates with treasury limits, maintains immutable audit log. |

## 3. Workflow Orchestration
1. `load_sources` normalises inputs and tags provenance.
2. `match_records` aligns holdings by ISIN/account/pay date.
3. `evaluate_matches` assigns rule-based reason codes.
4. `BreakAdvisor` enriches each break with LLM insight (or rule fallback) + writes to artefacts.
5. `summarize_breaks` produces an executive brief (`out/recon_llm_brief.md`).
6. Downstream systems consume CSV/JSON for automation; humans consult Markdown briefs for triage.

## 4. Automation Roadmap
- **Today:** LLM assistant produces remediation guidance + automation suitability while deterministic engine guards accuracy.
- **Near-term:** Introduce retrieval-augmented memory of prior resolutions and integrate ServiceNow/Jira ticket drafting via tools API.
- **Long-term:** Autonomous reconciliation bots execute low-risk adjustments under policy-as-code guardrails, with real-time monitoring dashboards and kill-switch controls.

## 5. Risk & Governance Anchors
- Budget monitoring hooks enforce <$15 API usage by caching responses and batching prompts.
- Access limited via environment variables; secrets never written to disk.
- Confidence score + automation mode allow NBIM to throttle autonomy per desk.
- All outputs are persisted as Markdown/JSON to enable audit replay and regulatory review.
