from flask import Blueprint, current_app, request, jsonify

from app.services.rag_service import (
    retrieve_and_generate,
    retrieve,
    retrieve_and_generate_custom,
    langchain_rag,
)

rag_bp = Blueprint("rag", __name__)


@rag_bp.route("/retrieve-and-generate", methods=["POST"])
def rag_retrieve_and_generate():
    body = request.json or {}
    errors = []
    if not body.get("query"):
        errors.append("query is required")
    kb_id = body.get("kb_id") or current_app.config["KNOWLEDGE_BASE_ID"]
    if not kb_id:
        errors.append("kb_id is required (provide in body or create a KB first)")
    if errors:
        return jsonify({"error": "Missing required fields", "fields": errors}), 400

    response = retrieve_and_generate(
        query=body["query"],
        kb_id=kb_id,
        model_id=body.get("model_id", "amazon.nova-lite-v1:0"),
        region_id=body.get("region_id"),
        session_id=body.get("session_id"),
    )

    generated_text = response["output"]["text"]
    citations = response.get("citations", [])
    contexts = []
    for citation in citations:
        for ref in citation.get("retrievedReferences", []):
            contexts.append(ref["content"]["text"])

    return jsonify({
        "answer": generated_text,
        "contexts": contexts,
    })


@rag_bp.route("/retrieve", methods=["POST"])
def rag_retrieve():
    body = request.json or {}
    errors = []
    if not body.get("query"):
        errors.append("query is required")
    kb_id = body.get("kb_id") or current_app.config["KNOWLEDGE_BASE_ID"]
    if not kb_id:
        errors.append("kb_id is required (provide in body or create a KB first)")
    if errors:
        return jsonify({"error": "Missing required fields", "fields": errors}), 400

    response = retrieve(
        query=body["query"],
        kb_id=kb_id,
        number_of_results=body.get("number_of_results", 5),
        search_type=body.get("search_type"),
    )

    return jsonify({
        "retrieval_results": response.get("retrievalResults", []),
    })


@rag_bp.route("/generate", methods=["POST"])
def rag_generate():
    body = request.json or {}
    errors = []
    if not body.get("query"):
        errors.append("query is required")
    kb_id = body.get("kb_id") or current_app.config["KNOWLEDGE_BASE_ID"]
    if not kb_id:
        errors.append("kb_id is required (provide in body or create a KB first)")
    if errors:
        return jsonify({"error": "Missing required fields", "fields": errors}), 400

    result = retrieve_and_generate_custom(
        query=body["query"],
        kb_id=kb_id,
        number_of_results=body.get("number_of_results", 5),
        model_id=body.get("model_id", "amazon.nova-lite-v1:0"),
        search_type=body.get("search_type"),
    )

    return jsonify(result)


@rag_bp.route("/langchain", methods=["POST"])
def rag_langchain():
    body = request.json or {}
    errors = []
    if not body.get("query"):
        errors.append("query is required")
    kb_id = body.get("kb_id") or current_app.config["KNOWLEDGE_BASE_ID"]
    if not kb_id:
        errors.append("kb_id is required (provide in body or create a KB first)")
    if errors:
        return jsonify({"error": "Missing required fields", "fields": errors}), 400

    result = langchain_rag(
        query=body["query"],
        kb_id=kb_id,
        model_id=body.get("model_id", "amazon.nova-lite-v1:0"),
        number_of_results=body.get("number_of_results", 4),
        search_type=body.get("search_type", "SEMANTIC"),
    )

    return jsonify(result)
