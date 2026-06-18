from flask import Blueprint, request, jsonify

from app.config import _save_kb_id, _save_config, _load_config
from app.services.s3_service import (
    create_s3_bucket,
    download_sample_documents,
    upload_directory_to_s3,
)
from app.services.oss_service import create_opensearch_collection
from app.services.bedrock_service import (
    create_knowledge_base,
    create_data_source,
    start_ingestion_job,
    get_ingestion_job_status,
    list_knowledge_bases,
)

kb_bp = Blueprint("kb", __name__)


@kb_bp.route("/create-bucket", methods=["POST"])
def create_bucket():
    body = request.json or {}
    bucket_name = body.get("bucket_name", "mmt-invoices")
    region = body.get("region")
    result = create_s3_bucket(bucket_name, region)
    return jsonify({"message": "Bucket created", **result})


@kb_bp.route("/download-documents", methods=["POST"])
def download_docs():
    data_dir = request.json.get("data_dir", "./data") if request.json else "./data"
    files = download_sample_documents(data_dir)
    return jsonify({"message": "Documents downloaded", "files": files})


@kb_bp.route("/upload-to-s3", methods=["POST"])
def upload_to_s3():
    body = request.json or {}
    local_path = body.get("local_path", "./data")
    bucket_name = body.get("bucket_name", "")
    if not bucket_name:
        return jsonify({"error": "bucket_name is required"}), 400
    uploaded = upload_directory_to_s3(local_path, bucket_name)
    return jsonify({"message": "Upload complete", "files": uploaded})


@kb_bp.route("/create-collection", methods=["POST"])
def create_collection():
    existing = _load_config()
    if existing.get("collection_id") and existing.get("collection_arn"):
        return jsonify({
            "message": "Collection already exists",
            "collection_name": existing.get("collection_name", ""),
            "collection_id": existing["collection_id"],
            "collection_arn": existing["collection_arn"],
        })
    body = request.json or {}
    name = body.get("vector_store_name")
    result = create_opensearch_collection(name)
    _save_config(
        collection_name=result["collection_name"],
        collection_id=result["collection_id"],
        collection_arn=result["collection_arn"],
    )
    return jsonify({"message": "Collection created", **result})


@kb_bp.route("/create", methods=["POST"])
def create_kb():
    existing = _load_config()
    if existing.get("kb_id"):
        return jsonify({"message": "Knowledge base already exists", "kb_id": existing["kb_id"]})

    body = request.json or {}
    errors = []
    if not body.get("bucket_name"):
        errors.append("bucket_name is required")
    if not body.get("collection_arn"):
        errors.append("collection_arn is required")
    if not body.get("collection_id"):
        errors.append("collection_id is required")
    if errors:
        return jsonify({"error": "Missing required fields", "fields": errors}), 400

    kb_id = create_knowledge_base(
        bucket_name=body["bucket_name"],
        collection_arn=body["collection_arn"],
        collection_id=body["collection_id"],
        vector_store_name=body.get("vector_store_name"),
        kb_name=body.get("kb_name"),
        kb_description=body.get("kb_description"),
    )
    _save_kb_id(kb_id)
    return jsonify({"message": "Knowledge base created", "kb_id": kb_id})


@kb_bp.route("/create-data-source", methods=["POST"])
def create_ds():
    existing = _load_config()
    if existing.get("ds_id"):
        return jsonify({"message": "Data source already exists", "data_source_id": existing["ds_id"]})

    body = request.json or {}
    if not body.get("kb_id"):
        return jsonify({"error": "kb_id is required"}), 400
    if not body.get("bucket_name"):
        return jsonify({"error": "bucket_name is required"}), 400
    ds_id = create_data_source(body["kb_id"], body["bucket_name"], body.get("ds_name"))
    _save_config(ds_id=ds_id)
    return jsonify({"message": "Data source created", "data_source_id": ds_id})


@kb_bp.route("/start-ingestion", methods=["POST"])
def start_ingestion():
    body = request.json or {}
    if not body.get("kb_id"):
        return jsonify({"error": "kb_id is required"}), 400
    if not body.get("ds_id"):
        return jsonify({"error": "ds_id is required"}), 400
    job_id = start_ingestion_job(body["kb_id"], body["ds_id"])
    return jsonify({"message": "Ingestion job started", "job_id": job_id})


@kb_bp.route("/ingestion-status", methods=["GET"])
def ingestion_status():
    kb_id = request.args.get("kb_id")
    ds_id = request.args.get("ds_id")
    job_id = request.args.get("job_id")
    if not all([kb_id, ds_id, job_id]):
        return jsonify({"error": "kb_id, ds_id, and job_id are required"}), 400
    status = get_ingestion_job_status(kb_id, ds_id, job_id)
    return jsonify({"status": status})


@kb_bp.route("/list", methods=["GET"])
def list_kb():
    kbs = list_knowledge_bases()
    return jsonify({"knowledge_bases": kbs})
