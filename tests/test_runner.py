import json

import pytest

from azure_ai_foundry_demo.agents.runner import AzureAgentRunner


def test_parse_function_arguments_returns_empty_dict_for_blank_input():
    assert AzureAgentRunner._parse_function_arguments(None) == {}
    assert AzureAgentRunner._parse_function_arguments("") == {}
    assert AzureAgentRunner._parse_function_arguments("   ") == {}


def test_parse_function_arguments_requires_object():
    with pytest.raises(json.JSONDecodeError):
        AzureAgentRunner._parse_function_arguments("[]")



def test_parse_function_arguments_parses_json_object():
    result = AzureAgentRunner._parse_function_arguments('{"ticker": "MSFT"}')
    assert result == {"ticker": "MSFT"}
