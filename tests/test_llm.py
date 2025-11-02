import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from recon.llm import (
    _extract_json_payload,
    annotate_break,
    set_structured_client_for_testing,
)
from recon.models import DividendRecord


class _ContentObject:
    def __init__(self, text: str):
        self.text = text


class _MessageObject:
    def __init__(self, text: str):
        self.content = [_ContentObject(text)]


class _OutputWithContent:
    def __init__(self, text: str):
        self.content = [_ContentObject(text)]


class _OutputWithMessage:
    def __init__(self, text: str):
        self.message = _MessageObject(text)


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(output=[_OutputWithContent('{"foo": 1}')]),
        SimpleNamespace(outputs=[_OutputWithContent('{"foo": 1}')]),
        SimpleNamespace(output=[_OutputWithMessage('{"foo": 1}')]),
        SimpleNamespace(choices=[_OutputWithContent('{"foo": 1}')]),
    ],
)
def test_extract_json_payload_handles_various_sdk_shapes(response):
    payload = _extract_json_payload(response)
    assert payload == {"foo": 1}


def test_extract_json_payload_ignores_non_json_blocks():
    response = SimpleNamespace(
        outputs=[
            _OutputWithContent("not-json"),
            _OutputWithContent(json.dumps({"foo": "bar"})),
        ]
    )

    payload = _extract_json_payload(response)
    assert payload == {"foo": "bar"}


def _sample_record(*, source: str, amount: str, currency: str, status: str) -> DividendRecord:
    return DividendRecord(
        source=source,
        trade_id="T1",
        isin="NO0000000001",
        pay_date=date(2024, 1, 5),
        account="ACCT-1",
        amount=Decimal(amount),
        currency=currency,
        status=status,
    )


def test_annotate_break_uses_fallback_summary_for_amount_difference():
    class _NoSummaryClient:
        def request(self, *, messages, schema):  # type: ignore[override]
            return {"severity": "low", "actions": []}

    set_structured_client_for_testing(_NoSummaryClient())
    try:
        nbim = _sample_record(source="NBIM", amount="100.00", currency="NOK", status="PAID")
        custodian = _sample_record(
            source="CUSTODIAN", amount="120.00", currency="NOK", status="PAID"
        )
        annotation = annotate_break("AMOUNT_DIFFERENCE", nbim, custodian)
    finally:
        set_structured_client_for_testing(None)

    expected = (
        "Amounts differ for ISIN NO0000000001, account ACCT-1, pay date 2024-01-05: "
        "NBIM reports 100.00 NOK while custodian reports 120.00 NOK."
    )
    assert annotation.explanation == expected
    assert annotation.severity == "low"


def test_annotate_break_uses_fallback_summary_for_missing_custodian_record():
    class _NoSummaryClient:
        def request(self, *, messages, schema):  # type: ignore[override]
            return {"severity": "high", "actions": []}

    set_structured_client_for_testing(_NoSummaryClient())
    try:
        nbim = _sample_record(source="NBIM", amount="75.50", currency="USD", status="PENDING")
        annotation = annotate_break("MISSING_IN_CUSTODIAN", nbim, None)
    finally:
        set_structured_client_for_testing(None)

    expected = (
        "NBIM has a dividend of 75.50 USD for ISIN NO0000000001, account ACCT-1, pay "
        "date 2024-01-05, but the custodian record is missing."
    )
    assert annotation.explanation == expected
    assert annotation.severity == "high"
