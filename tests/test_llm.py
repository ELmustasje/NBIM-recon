import json
from types import SimpleNamespace

import pytest

from recon.llm import _extract_json_payload


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
