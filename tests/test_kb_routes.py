from unittest.mock import patch


class TestCreateBucket:
    ENDPOINT = "/api/v1/kb/create-bucket"

    @patch("app.routes.kb_routes.create_s3_bucket")
    def test_success(self, mock_create, client):
        mock_create.return_value = {"bucket": "my-bucket", "region": "us-east-1"}
        resp = client.post(self.ENDPOINT, json={"bucket_name": "my-bucket"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["bucket"] == "my-bucket"


class TestDownloadDocs:
    ENDPOINT = "/api/v1/kb/download-documents"

    @patch("app.routes.kb_routes.download_sample_documents")
    def test_success(self, mock_download, client):
        mock_download.return_value = ["file1.pdf", "file2.pdf"]
        resp = client.post(self.ENDPOINT, json={"data_dir": "./data"})
        assert resp.status_code == 200
        assert len(resp.get_json()["files"]) == 2


class TestUploadToS3:
    ENDPOINT = "/api/v1/kb/upload-to-s3"

    def test_missing_bucket_name(self, client):
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 400

    @patch("app.routes.kb_routes.upload_directory_to_s3")
    def test_success(self, mock_upload, client):
        mock_upload.return_value = ["a.pdf", "b.pdf"]
        resp = client.post(self.ENDPOINT, json={"bucket_name": "my-bucket"})
        assert resp.status_code == 200
        assert len(resp.get_json()["files"]) == 2


class TestCreateCollection:
    ENDPOINT = "/api/v1/kb/create-collection"

    @patch("app.routes.kb_routes.create_opensearch_collection")
    def test_success(self, mock_create, client):
        mock_create.return_value = {
            "collection_name": "my-coll",
            "collection_id": "coll-1",
            "collection_arn": "arn:aws:oss:us-east-1:123:collection/coll-1",
        }
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["collection_id"] == "coll-1"

    @patch("app.routes.kb_routes._load_config")
    def test_already_exists(self, mock_load, client):
        mock_load.return_value = {
            "collection_id": "existing-coll",
            "collection_arn": "arn:aws:oss:us-east-1:123:collection/existing-coll",
        }
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 200
        assert resp.get_json()["collection_id"] == "existing-coll"


class TestCreateKB:
    ENDPOINT = "/api/v1/kb/create"

    @patch("app.routes.kb_routes._load_config", return_value={})
    def test_missing_fields(self, mock_load, client):
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 400

    @patch("app.routes.kb_routes._load_config")
    def test_already_exists(self, mock_load, client):
        mock_load.return_value = {"kb_id": "existing-kb"}
        resp = client.post(self.ENDPOINT, json={
            "bucket_name": "b", "collection_arn": "a", "collection_id": "c"
        })
        assert resp.status_code == 200
        assert resp.get_json()["kb_id"] == "existing-kb"

    @patch("app.routes.kb_routes.create_knowledge_base")
    @patch("app.routes.kb_routes._load_config")
    def test_success(self, mock_load, mock_create, client):
        mock_load.return_value = {}
        mock_create.return_value = "new-kb-1"
        resp = client.post(self.ENDPOINT, json={
            "bucket_name": "b", "collection_arn": "a", "collection_id": "c"
        })
        assert resp.status_code == 200
        assert resp.get_json()["kb_id"] == "new-kb-1"


class TestCreateDataSource:
    ENDPOINT = "/api/v1/kb/create-data-source"

    @patch("app.routes.kb_routes._load_config", return_value={})
    def test_missing_fields(self, mock_load, client):
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 400

    @patch("app.routes.kb_routes._load_config")
    def test_already_exists(self, mock_load, client):
        mock_load.return_value = {"ds_id": "existing-ds"}
        resp = client.post(self.ENDPOINT, json={"kb_id": "k", "bucket_name": "b"})
        assert resp.status_code == 200
        assert resp.get_json()["data_source_id"] == "existing-ds"

    @patch("app.routes.kb_routes.create_data_source")
    @patch("app.routes.kb_routes._load_config")
    def test_success(self, mock_load, mock_create, client):
        mock_load.return_value = {}
        mock_create.return_value = "new-ds-1"
        resp = client.post(self.ENDPOINT, json={"kb_id": "k", "bucket_name": "b"})
        assert resp.status_code == 200
        assert resp.get_json()["data_source_id"] == "new-ds-1"


class TestStartIngestion:
    ENDPOINT = "/api/v1/kb/start-ingestion"

    def test_missing_fields(self, client):
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 400

    @patch("app.routes.kb_routes.start_ingestion_job")
    def test_success(self, mock_start, client):
        mock_start.return_value = "job-1"
        resp = client.post(self.ENDPOINT, json={"kb_id": "k", "ds_id": "d"})
        assert resp.status_code == 200
        assert resp.get_json()["job_id"] == "job-1"


class TestIngestionStatus:
    ENDPOINT = "/api/v1/kb/ingestion-status"

    def test_missing_params(self, client):
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 400

    @patch("app.routes.kb_routes.get_ingestion_job_status")
    def test_success(self, mock_status, client):
        mock_status.return_value = "COMPLETE"
        resp = client.get(self.ENDPOINT, query_string={
            "kb_id": "k", "ds_id": "d", "job_id": "j"
        })
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "COMPLETE"


class TestList:
    ENDPOINT = "/api/v1/kb/list"

    @patch("app.routes.kb_routes.list_knowledge_bases")
    def test_success(self, mock_list, client):
        mock_list.return_value = [{"name": "kb-1", "knowledgeBaseId": "id-1"}]
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        assert len(resp.get_json()["knowledge_bases"]) == 1


class TestHealth:
    ENDPOINT = "/health"

    def test_success(self, client):
        resp = client.get(self.ENDPOINT)
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}
