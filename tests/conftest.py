import json
from unittest.mock import patch

import pytest
from app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "KNOWLEDGE_BASE_ID": "test-kb-id",
    })
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def mock_bedrock_agent_runtime():
    with patch("app.services.rag_service.boto3.client") as mock:
        client = mock.return_value
        yield client


@pytest.fixture
def mock_bedrock_agent_runtime_retrieve_and_generate(mock_bedrock_agent_runtime):
    mock_bedrock_agent_runtime.retrieve_and_generate.return_value = {
        "output": {"text": "You spent £120 on train tickets."},
        "citations": [
            {
                "retrievedReferences": [
                    {"content": {"text": "Ticket from London to Edinburgh cost £120"}}
                ]
            }
        ],
    }
    return mock_bedrock_agent_runtime


@pytest.fixture
def mock_bedrock_agent_runtime_retrieve(mock_bedrock_agent_runtime):
    mock_bedrock_agent_runtime.retrieve.return_value = {
        "retrievalResults": [
            {"content": {"text": "Ticket from London to Edinburgh cost £120"}},
            {"content": {"text": "Refund for cancelled booking: £45"}},
        ]
    }
    return mock_bedrock_agent_runtime


@pytest.fixture
def mock_bedrock_runtime():
    with patch("app.services.rag_service.boto3.client") as mock:
        client = mock.return_value
        client.invoke_model.return_value = {
            "body": type("Bytes", (), {"read": lambda s: json.dumps({
                "output": {"message": {"content": [{"text": "You spent £120."}]}}
            }).encode()})()
        }
        yield client


@pytest.fixture
def mock_region():
    with patch("boto3.session.Session.region_name", "us-east-1"):
        yield
