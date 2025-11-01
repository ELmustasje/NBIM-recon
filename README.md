# NBIM Recon


## Quick start

```bash
PYTHONPATH=$(pwd) ./bin/recon run
```

Outputs are written to `out/`:

- `recon_breaks.csv`
- `recon_breaks.json`
- `recon_report.md`

See [runbook/README.md](runbook/README.md) for the operational walkthrough.

## Development

- Python 3.12+
- Optional tooling: `pip install -r requirements-dev.txt`
- Run the custom coverage gate: `python tools/run_tests_with_trace.py`
