import json

import boto3
from botocore.client import Config
from app.prompts import FINANCIAL_ADVISOR_SYSTEM_PROMPT, LANGCHAIN_RAG_SYSTEM_PROMPT, LANGCHAIN_RAG_HUMAN_PROMPT


def _get_bedrock_runtime_client():
    return boto3.client("bedrock-runtime")


def _get_bedrock_agent_runtime_client():
    config = Config(connect_timeout=120, read_timeout=120, retries={"max_attempts": 0})
    return boto3.client("bedrock-agent-runtime", config=config)


def retrieve_and_generate(
    query: str,
    kb_id: str,
    model_id: str = "amazon.nova-lite-v1:0",
    region_id: str = None,
    session_id: str = None,
):
    if region_id is None:
        region_id = boto3.session.Session().region_name
    client = _get_bedrock_agent_runtime_client()
    model_arn = f"arn:aws:bedrock:{region_id}::foundation-model/{model_id}"
    kwargs = {
        "input": {"text": query},
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": model_arn,
            },
        },
    }
    if session_id:
        kwargs["sessionId"] = session_id
    return client.retrieve_and_generate(**kwargs)


def retrieve(
    query: str,
    kb_id: str,
    number_of_results: int = 5,
    search_type: str = None,
):
    client = _get_bedrock_agent_runtime_client()
    retrieval_config = {
        "vectorSearchConfiguration": {
            "numberOfResults": number_of_results,
        }
    }
    if search_type:
        retrieval_config["vectorSearchConfiguration"]["overrideSearchType"] = search_type

    response = client.retrieve(
        retrievalQuery={"text": query},
        knowledgeBaseId=kb_id,
        retrievalConfiguration=retrieval_config,
    )
    return response


def get_contexts_from_retrieval(retrieval_results: list) -> list:
    contexts = []
    for result in retrieval_results:
        contexts.append(result["content"]["text"])
    return contexts


def generate_answer(
    query: str,
    contexts: list,
    model_id: str = "amazon.nova-lite-v1:0",
    max_tokens: int = 512,
    temperature: float = 0.5,
):
    client = _get_bedrock_runtime_client()
    context_str = "\n".join(contexts)
    prompt = FINANCIAL_ADVISOR_SYSTEM_PROMPT.format(contexts=context_str, query=query)

    messages = [{"role": "user", "content": [{"text": prompt}]}]
    payload = json.dumps({
        "messages": messages,
        "inferenceConfig": {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
        },
    })

    response = client.invoke_model(
        body=payload,
        modelId=model_id,
        accept="application/json",
        contentType="application/json",
    )
    response_body = json.loads(response.get("body").read())
    return response_body["output"]["message"]["content"][0]["text"]


def retrieve_and_generate_custom(
    query: str,
    kb_id: str,
    number_of_results: int = 5,
    model_id: str = "amazon.nova-lite-v1:0",
    search_type: str = None,
):
    retrieval_response = retrieve(query, kb_id, number_of_results, search_type)
    retrieval_results = retrieval_response["retrievalResults"]
    contexts = get_contexts_from_retrieval(retrieval_results)
    answer = generate_answer(query, contexts, model_id)
    return {
        "answer": answer,
        "contexts": contexts,
        "retrieval_results": retrieval_results,
    }


def langchain_rag(
    query: str,
    kb_id: str,
    model_id: str = "amazon.nova-lite-v1:0",
    number_of_results: int = 4,
    search_type: str = "SEMANTIC",
):
    try:
        from langchain_aws import ChatBedrock
        from langchain_aws.retrievers import AmazonKnowledgeBasesRetriever
        from langchain.chains import create_retrieval_chain
        from langchain.chains.combine_documents import create_stuff_documents_chain
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError:
        raise ImportError(
            "langchain-aws and langchain-core are required. "
            "Install with: pip install langchain langchain_aws langchain-core"
        )

    client = _get_bedrock_runtime_client()
    llm = ChatBedrock(model_id=model_id, client=client)

    retriever = AmazonKnowledgeBasesRetriever(
        knowledge_base_id=kb_id,
        retrieval_config={
            "vectorSearchConfiguration": {
                "numberOfResults": number_of_results,
                "overrideSearchType": search_type,
            }
        },
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", LANGCHAIN_RAG_SYSTEM_PROMPT),
        ("human", LANGCHAIN_RAG_HUMAN_PROMPT),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    response = rag_chain.invoke({"input": query})
    return {"answer": response["answer"], "context": [str(d) for d in response.get("context", [])]}
