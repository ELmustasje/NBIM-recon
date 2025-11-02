# NBIM Recon


## Quick start

```bash
PYTHONPATH=$(pwd) ./bin/recon run
```

Outputs are written to `out/`:

- `recon_breaks.csv`
- `recon_breaks.json`
- `recon_report.md`
- `recon_llm_brief.md` *(optional when LLM configured)*

### Enabling the LLM advisor

Set your OpenAI credentials before running the pipeline:

```bash
export OPENAI_API_KEY="sk-..."
# optional tuning
export RECON_LLM_MODEL="gpt-4o-mini"
export RECON_LLM_TEMPERATURE="0.1"
```

If the API key is absent or the SDK is not installed, the workflow gracefully falls back to deterministic explanations from `FALLBACK_LIBRARY`.

See [runbook/README.md](runbook/README.md) for the operational walkthrough.

Additional documentation:

- [Architecture vision](docs/architecture.md)
- [Prompt library](docs/prompts.md)
- [Analysis & recommendations](docs/analysis_recommendations.md)

## Development

- Python 3.12+
- Optional tooling: `pip install -r requirements-dev.txt`
- Run the custom coverage gate: `python tools/run_tests_with_trace.py`
