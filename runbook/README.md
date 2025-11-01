# Dividend Reconciliation Runbook

## One-command demo

```bash
PYTHONPATH=$(pwd) ./bin/recon run
```

This command ingests the sample NBIM and custodian files under `data/` and generates artefacts in `out/`.

## Expected outputs

![CLI output placeholder](images/demo.png)

The script produces:

- `out/recon_breaks.csv` – tabular view for spreadsheets
- `out/recon_breaks.json` – machine-readable payload for downstream systems
- `out/recon_report.md` – operator-facing summary with break explanations

Review the Markdown report first to see break severities and explanations. Use the CSV for detailed pivoting.

## Operational checklist

1. Ensure the NBIM and custodian files follow the headers in `data/`.
2. Adjust the tolerance via `--tolerance` when working with FX noise.
3. Escalate **high** severity breaks to the operations lead.
4. Attach the generated CSV and Markdown to ServiceNow incidents.
