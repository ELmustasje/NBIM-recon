# Dividend Reconciliation Runbook

## One-command demo

```bash
NBIM_OPENAI_API_KEY="sk-..." PYTHONPATH=$(pwd) python -m recon.cli run
```

This command ingests the sample NBIM and custodian files under `data/` and generates artefacts in `out/`.
If no API key is supplied the workflow falls back to deterministic explanations.

## Expected outputs

![CLI output placeholder](images/demo.png)

The script produces:

- `out/recon_breaks.csv` – tabular view for spreadsheets, including LLM-generated actions
- `out/recon_breaks.json` – machine-readable payload containing the raw LLM response
- `out/recon_report.md` – operator-facing summary with break explanations and escalation signal
- `out/recon_agent_plan.json` – queue of tasks for downstream specialist agents

Review the Markdown report first to see break severities and explanations. Use the CSV for detailed pivoting.

## Operational checklist

1. Ensure the NBIM and custodian files follow the headers in `data/`.
2. Adjust the tolerance via `--tolerance` when working with FX noise.
3. Escalate **high** severity breaks flagged with `needs_escalation = Yes`.
4. Use `recon_agent_plan.json` to seed downstream agents (custody liaison, static data, etc.).
5. Attach the generated CSV and Markdown to ServiceNow incidents.

## Further reading

- [Prompt catalogue](prompts.md)
- [Agentic architecture vision](architecture.md)
- [Risk analysis and recommendations](recommendations.md)
