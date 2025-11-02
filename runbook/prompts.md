# Prompt catalogue

## Break annotation prompt

- **Model**: configurable via `NBIM_OPENAI_MODEL` (default `gpt-4o-mini`)
- **System message**: "You are a senior NBIM operations analyst specialised in dividend reconciliations."
- **User message**:
  - Instruction to classify and explain the break and reply with JSON schema.
  - Embedded JSON payload with NBIM and custodian records plus reason code.
- **Response format**: enforced via the OpenAI JSON schema API to capture severity, summary, actions, confidence and escalation signal.

### Example payload

```json
{
  "reason_code": "AMOUNT_DIFFERENCE",
  "nbim_record": {
    "source": "NBIM",
    "trade_id": "NBIM-001",
    "isin": "NO000000001",
    "pay_date": "2024-03-14",
    "account": "12345",
    "amount": 125000.12,
    "currency": "USD",
    "status": "PAID"
  },
  "custodian_record": {
    "source": "CUSTODY",
    "trade_id": "CUST-001",
    "isin": "NO000000001",
    "pay_date": "2024-03-14",
    "account": "12345",
    "amount": 118000.10,
    "currency": "USD",
    "status": "PAID"
  }
}
```

The annotation agent transforms this data into remediation actions, severity and escalation advice used downstream by the control tower.

## Agent control tower

The `ControlTower` in `recon/agents.py` converts LLM output into actionable tasks. Each task is enriched with:

- Target agent persona (custody liaison, ledger ingestion, static data, cash allocator, settlement chaser).
- Priority derived from severity and escalation guidance.
- Structured payload for downstream automation or chat-based agents.

Tasks are exported as `out/recon_agent_plan.json` and can be consumed by orchestration frameworks such as LangChain, CrewAI or bespoke RPA bots.
