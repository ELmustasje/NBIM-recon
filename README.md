# NBIM Recon


## Quick start

```bash
NBIM_OPENAI_API_KEY="sk-..." PYTHONPATH=$(pwd) python -m recon.cli run
```

Outputs are written to `out/`:

- `recon_breaks.csv`
- `recon_breaks.json`
- `recon_report.md`
- `recon_agent_plan.json`

Set `NBIM_OPENAI_API_KEY` (or `OPENAI_API_KEY`) to enable LLM-enhanced explanations. Without it the system falls back to deterministic messaging.

See [runbook/README.md](runbook/README.md) for the operational walkthrough and additional documentation on prompts, architecture and risk analysis.

## Development

- Python 3.12+
- Optional tooling: `pip install -r requirements-dev.txt`
- Run the custom coverage gate: `python tools/run_tests_with_trace.py`
