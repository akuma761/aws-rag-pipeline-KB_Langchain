# API Flow

## Architecture

```
Streamlit App ──HTTP POST──> Flask Server ──boto3──> AWS Bedrock
                                │
                          ┌─────┴──────┐
                          │  Routes     │
                          │  (routes/)  │
                          └─────┬──────┘
                                │
                          ┌─────┴──────┐
                          │  Services   │
                          │ (services/) │
                          └─────┬──────┘
                                │
                          ┌─────┴──────┐
                          │  Prompts    │
                          │ (prompts.py)│
                          └────────────
```

## Endpoints

All routes are prefixed with `/api/v1/rag`.

### `POST /retrieve-and-generate`

- **Service fn**: `retrieve_and_generate()` in `rag_service.py`
- **Description**: Calls Bedrock's native `retrieve_and_generate` API — a single AWS API call that handles both retrieval from the Knowledge Base and generation using the specified model.
- **Prompt**: No custom prompt. Bedrock uses its own internal prompt.
- **Use when**: You want the simplest RAG flow and don't need to inspect or customise the context before generation.

**Payload:**
```json
{
  "query": "How much did I spend on trains?",
  "kb_id": "optional-knowledge-base-id",
  "model_id": "amazon.nova-lite-v1:0",
  "session_id": "optional-session-id"
}
```

**Flow:**
```
query ──> client.retrieve_and_generate(input={"text": query})
         └── Bedrock: retrieve chunks from KB + generate answer ──> response
```

---

### `POST /retrieve`

- **Service fn**: `retrieve()` in `rag_service.py`
- **Description**: Only fetches relevant context chunks from the Knowledge Base. No generation happens.
- **Use when**: You want to inspect raw retrieval quality, rerank results, filter chunks, or do your own downstream generation.

**Payload:**
```json
{
  "query": "How much did I spend on trains?",
  "kb_id": "optional-knowledge-base-id",
  "number_of_results": 5,
  "search_type": "HYBRID"
}
```

---

### `POST /generate`

- **Service fn**: `retrieve_and_generate_custom()` → `retrieve()` + `generate_answer()` in `rag_service.py`
- **Description**: Two-step process:
  1. `retrieve()` fetches context chunks from the KB.
  2. `generate_answer()` sends them to the model with `FINANCIAL_ADVISOR_SYSTEM_PROMPT`.
- **Prompt**: Uses `FINANCIAL_ADVISOR_SYSTEM_PROMPT` from `prompts.py`.
- **Use when**: You need control over the generation prompt, model parameters (temperature, max tokens), or want to inspect/edit the retrieved context before the model sees it.

**Prompt template (`FINANCIAL_ADVISOR_SYSTEM_PROMPT`):**
```
Human: You are a financial advisor AI system...
<context>
{contexts}
</context>

<question>
{query}
</question>
...
Assistant:
```

**Flow:**
```
query ──> retrieve(query) ──> context chunks
         └── generate_answer(query, contexts)
                  └── prompt.format(contexts=..., query=...)
                  └── client.invoke_model(body=prompt)
                  └── answer
```

---

### `POST /langchain`

- **Service fn**: `langchain_rag()` in `rag_service.py`
- **Description**: Uses LangChain's `AmazonKnowledgeBasesRetriever` + `create_stuff_documents_chain` with a `ChatBedrock` LLM.
- **Prompt**: Uses `LANGCHAIN_RAG_SYSTEM_PROMPT` and `LANGCHAIN_RAG_HUMAN_PROMPT` from `prompts.py`.
- **Use when**: You prefer LangChain abstractions or want to add memory, routing, or other chain composition.

**Prompt templates:**
```
System: You are an assistant for question-answering tasks...
{context}

Human: {input}
```

---

## Streamlit → API Flow

The Streamlit app (`streamlit_app.py`) only calls `/retrieve-and-generate`:

```
User types question ──> st.chat_input()
                      └── POST /api/v1/rag/retrieve-and-generate
                          json={"query": "user question", "kb_id": "..."}
                          └── Flask extracts query
                              └── retrieve_and_generate(query)
                                  └── Bedrock retrieve_and_generate
                                      └── returns answer text
                          └── response: {"answer": "...", "contexts": [...]}
                      └── st.markdown(answer)
```

## AWS Clients

| Client | Service | Used in |
|--------|---------|---------|
| `bedrock-agent-runtime` | `retrieve`, `retrieve_and_generate` | `rag_service.py` |
| `bedrock-runtime` | `invoke_model` | `generate_answer()` in `rag_service.py` |
