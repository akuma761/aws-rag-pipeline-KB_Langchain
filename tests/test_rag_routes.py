import json
from unittest.mock import patch


class TestRetrieveAndGenerate:
    ENDPOINT = "/api/v1/rag/retrieve-and-generate"

    def test_missing_query_returns_400(self, client):
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 400

    def test_missing_kb_id_returns_400(self, client, app):
        app.config["KNOWLEDGE_BASE_ID"] = ""
        resp = client.post(self.ENDPOINT, json={"query": "hello"})
        assert resp.status_code == 400

    @patch("app.services.rag_service.boto3.session.Session.region_name", "us-east-1")
    @patch("app.services.rag_service.boto3.client")
    def test_success(self, mock_client, client):
        mock_client.return_value.retrieve_and_generate.return_value = {
            "output": {"text": "You spent £120."},
            "citations": [
                {
                    "retrievedReferences": [
                        {"content": {"text": "London to Edinburgh cost £120"}}
                    ]
                }
            ],
        }
        resp = client.post(self.ENDPOINT, json={"query": "How much?", "kb_id": "kb-1"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["answer"] == "You spent £120."
        assert len(data["contexts"]) == 1

    @patch("app.services.rag_service.boto3.session.Session.region_name", "us-east-1")
    @patch("app.services.rag_service.boto3.client")
    def test_success_without_citations(self, mock_client, client):
        mock_client.return_value.retrieve_and_generate.return_value = {
            "output": {"text": "No citations."},
        }
        resp = client.post(self.ENDPOINT, json={"query": "Any?", "kb_id": "kb-1"})
        assert resp.status_code == 200
        assert resp.get_json()["contexts"] == []


class TestRetrieve:
    ENDPOINT = "/api/v1/rag/retrieve"

    def test_missing_query_returns_400(self, client):
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 400

    @patch("app.services.rag_service.boto3.client")
    def test_success(self, mock_client, client):
        mock_client.return_value.retrieve.return_value = {
            "retrievalResults": [
                {"content": {"text": "Result 1"}},
                {"content": {"text": "Result 2"}},
            ]
        }
        resp = client.post(self.ENDPOINT, json={"query": "test", "kb_id": "kb-1"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["retrieval_results"]) == 2


class TestGenerate:
    ENDPOINT = "/api/v1/rag/generate"

    def test_missing_query_returns_400(self, client):
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 400

    @patch("app.services.rag_service.boto3.client")
    def test_success(self, mock_client, client, mock_region):
        mock_client.return_value.retrieve.return_value = {
            "retrievalResults": [{"content": {"text": "source text"}}]
        }
        mock_client.return_value.invoke_model.return_value = {
            "body": type("Bytes", (), {"read": lambda s: json.dumps({
                "output": {"message": {"content": [{"text": "Answer text"}]}}
            }).encode()})()
        }
        resp = client.post(self.ENDPOINT, json={"query": "test", "kb_id": "kb-1"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "answer" in data
        assert "contexts" in data


class TestLangchain:
    ENDPOINT = "/api/v1/rag/langchain"

    def test_missing_query_returns_400(self, client):
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 400

    def test_missing_langchain_deps(self, client):
        resp = client.post(self.ENDPOINT, json={"query": "test", "kb_id": "kb-1"})
        assert resp.status_code == 500
