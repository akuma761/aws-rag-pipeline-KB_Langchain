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
    """Uses Bedrock's native retrieve_and_generate (single API call).
    Use when: you want the simplest RAG flow and don't need custom prompt control
    or to inspect the retrieved context before generation."""
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
    """Only retrieves context chunks from the knowledge base, no generation.
    Use when: you want to inspect raw retrieval results, or when you'll do your
    own downstream processing (reranking, filtering, etc.) before generating."""

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
    """Two-step: retrieve + generate with a custom prompt.
    Use when: you want full control over the generation prompt
    (FINANCIAL_ADVISOR_SYSTEM_PROMPT), model parameters, or need to
    inspect/edit the retrieved contexts before the model responds."""
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
    """LangChain-based RAG: uses AmazonKnowledgeBasesRetriever + stuff documents chain.
    Use when: you prefer LangChain abstractions, want to add memory/chaining, or
    are already using LangChain elsewhere in your project."""
    body = request.json or {}
    errors = []
    if not body.get("query"):
        errors.append("query is required")
    kb_id = body.get("kb_id") or current_app.config["KNOWLEDGE_BASE_ID"]
    if not kb_id:
        errors.append("kb_id is required (provide in body or create a KB first)")
    if errors:
        return jsonify({"error": "Missing required fields", "fields": errors}), 400

    try:
        result = langchain_rag(
            query=body["query"],
            kb_id=kb_id,
            model_id=body.get("model_id", "amazon.nova-lite-v1:0"),
            number_of_results=body.get("number_of_results", 4),
            search_type=body.get("search_type", "SEMANTIC"),
        )
    except ImportError as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(result)
