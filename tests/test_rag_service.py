import json
from unittest.mock import patch

import pytest

from app.services.rag_service import get_contexts_from_retrieval
from app.prompts import FINANCIAL_ADVISOR_SYSTEM_PROMPT, LANGCHAIN_RAG_SYSTEM_PROMPT


def test_get_contexts_from_retrieval():
    results = [
        {"content": {"text": "First document chunk"}},
        {"content": {"text": "Second document chunk"}},
    ]
    contexts = get_contexts_from_retrieval(results)
    assert contexts == ["First document chunk", "Second document chunk"]


def test_get_contexts_from_retrieval_empty():
    assert get_contexts_from_retrieval([]) == []


def test_financial_advisor_prompt_format():
    prompt = FINANCIAL_ADVISOR_SYSTEM_PROMPT.format(
        contexts="ctx1\nctx2", query="How much did I spend?"
    )
    assert "ctx1" in prompt
    assert "ctx2" in prompt
    assert "How much did I spend?" in prompt


def test_langchain_prompt_has_required_keys():
    assert "{context}" in LANGCHAIN_RAG_SYSTEM_PROMPT


@patch("app.services.rag_service.boto3.client")
def test_retrieve(mock_client):
    from app.services.rag_service import retrieve

    mock_client.return_value.retrieve.return_value = {
        "retrievalResults": [{"content": {"text": "result"}}]
    }

    result = retrieve(query="test", kb_id="kb-1", number_of_results=3, search_type="SEMANTIC")
    mock_client.return_value.retrieve.assert_called_once_with(
        retrievalQuery={"text": "test"},
        knowledgeBaseId="kb-1",
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 3,
                "overrideSearchType": "SEMANTIC",
            }
        },
    )
    assert result["retrievalResults"][0]["content"]["text"] == "result"


@patch("app.services.rag_service.boto3.client")
def test_retrieve_without_search_type(mock_client):
    from app.services.rag_service import retrieve

    mock_client.return_value.retrieve.return_value = {"retrievalResults": []}

    retrieve(query="test", kb_id="kb-1")

    call_kwargs = mock_client.return_value.retrieve.call_args[1]
    assert "overrideSearchType" not in call_kwargs["retrievalConfiguration"]["vectorSearchConfiguration"]


@patch("app.services.rag_service.boto3.client")
def test_retrieve_and_generate(mock_client):
    from app.services.rag_service import retrieve_and_generate

    mock_client.return_value.retrieve_and_generate.return_value = {
        "output": {"text": "Generated answer"},
        "citations": [{"retrievedReferences": [{"content": {"text": "source"}}]}],
    }

    with patch("boto3.session.Session.region_name", "us-east-1"):
        result = retrieve_and_generate(query="test", kb_id="kb-1")

    assert result["output"]["text"] == "Generated answer"


@patch("app.services.rag_service.boto3.client")
def test_generate_answer(mock_client):
    from app.services.rag_service import generate_answer

    mock_client.return_value.invoke_model.return_value = {
        "body": type("Bytes", (), {"read": lambda s: json.dumps({
            "output": {"message": {"content": [{"text": "You spent £120."}]}}
        }).encode()})()
    }

    answer = generate_answer(
        query="How much?",
        contexts=["Ticket cost £120"],
        model_id="amazon.nova-lite-v1:0",
    )
    assert answer == "You spent £120."


@patch("app.services.rag_service.get_contexts_from_retrieval", return_value=["ctx1"])
@patch("app.services.rag_service.generate_answer", return_value="Generated")
@patch("app.services.rag_service.boto3.client")
def test_retrieve_and_generate_custom(mock_client, mock_generate, mock_contexts):
    from app.services.rag_service import retrieve_and_generate_custom

    mock_client.return_value.retrieve.return_value = {
        "retrievalResults": [{"content": {"text": "ctx1"}}]
    }

    result = retrieve_and_generate_custom(
        query="test", kb_id="kb-1", number_of_results=3, model_id="amazon.nova-lite-v1:0"
    )

    assert result["answer"] == "Generated"
    assert result["contexts"] == ["ctx1"]
    assert len(result["retrieval_results"]) == 1
