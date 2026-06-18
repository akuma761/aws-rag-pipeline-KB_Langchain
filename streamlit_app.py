import os
import json

import streamlit as st
import requests

API_BASE = os.getenv("FLASK_API_URL", "http://localhost:5000")
KB_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "app", "kb_config.json")

QUERY_MODES = {
    "Retrieve & Generate (Managed)": "/api/v1/rag/retrieve-and-generate",
    "Custom Generate (Advisor Prompt)": "/api/v1/rag/generate",
    "LangChain RAG": "/api/v1/rag/langchain",
    "Retrieve (Raw Chunks)": "/api/v1/rag/retrieve",
}

st.set_page_config(page_title="MMT Invoice RAG", page_icon="🧾", layout="wide")
st.title("🧾 MakeMyTrip Invoice Query")

_default_kb_id = os.getenv("KNOWLEDGE_BASE_ID", "")
if not _default_kb_id:
    try:
        with open(KB_CONFIG_PATH) as f:
            _default_kb_id = json.load(f).get("kb_id", "")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

with st.sidebar:
    st.header("Configuration")
    api_url = st.text_input("Flask API URL", value=API_BASE)
    kb_id = st.text_input("Knowledge Base ID", value=_default_kb_id,
                          help="Auto-loaded from env / kb_config.json")

    mode_label = st.selectbox("Query Mode", list(QUERY_MODES.keys()))
    endpoint = QUERY_MODES[mode_label]

    with st.expander("Advanced"):
        num_results = st.number_input("Number of Results", min_value=1, max_value=50, value=5)
        model_id = st.text_input("Model ID", value="amazon.nova-lite-v1:0")
        search_type = st.selectbox("Search Type", ["SEMANTIC", "HYBRID"], index=0)

    st.divider()
    if st.button("🩺 Health Check"):
        try:
            r = requests.get(f"{api_url}/health", timeout=5)
            r.raise_for_status()
            st.success(f"Server OK — {r.json()}")
        except Exception as e:
            st.error(f"Server unreachable: {e}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "contexts" in msg and msg["contexts"]:
            with st.expander("📄 Retrieved Contexts"):
                for i, ctx in enumerate(msg["contexts"], 1):
                    st.text_area(f"Context {i}", ctx, height=100, disabled=True)

with st.expander("💡 Example questions"):
    st.markdown("""
    - How much did I spend on train tickets last month?
    - What is the total amount of my cancelled bookings?
    - List all my trips from London to Edinburgh
    - Show me refunds processed in March
    - Which booking has the highest fare?
    """)

if prompt := st.chat_input("Ask a question about your MakeMyTrip invoices..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    payload = {"query": prompt}
    if kb_id:
        payload["kb_id"] = kb_id
    if num_results:
        payload["number_of_results"] = num_results
    if model_id:
        payload["model_id"] = model_id
    if search_type:
        payload["search_type"] = search_type

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳ Thinking...")

        try:
            resp = requests.post(f"{api_url}{endpoint}", json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            if endpoint == "/api/v1/rag/retrieve":
                results = data.get("retrieval_results", [])
                answer_lines = []
                contexts = []
                for i, r in enumerate(results, 1):
                    text = r.get("content", {}).get("text", str(r))
                    answer_lines.append(f"**Result {i}:**\n{text}")
                    contexts.append(text)
                answer = "\n\n".join(answer_lines)
            else:
                answer = data.get("answer", data.get("output", {}).get("text", str(data)))
                contexts = data.get("contexts", data.get("context", []))

            placeholder.markdown(answer)

            msg_entry = {"role": "assistant", "content": answer}
            if contexts:
                msg_entry["contexts"] = contexts
                with st.expander("📄 Retrieved Contexts"):
                    for i, ctx in enumerate(contexts, 1):
                        st.text_area(f"Context {i}", ctx, height=100, disabled=True)

            st.session_state.messages.append(msg_entry)

        except requests.exceptions.Timeout:
            placeholder.markdown("❌ Request timed out.")
            st.session_state.messages.append({"role": "assistant", "content": "❌ Request timed out."})
        except requests.exceptions.ConnectionError:
            placeholder.markdown(f"❌ Cannot connect to `{api_url}`. Is the Flask server running?")
            st.session_state.messages.append({"role": "assistant", "content": f"❌ Cannot connect to {api_url}."})
        except Exception as e:
            msg = f"❌ Error: {e}"
            if resp := getattr(e, "response", None):
                try:
                    detail = resp.json()
                    msg += f"\n\n**Server:**\n```json\n{json.dumps(detail, indent=2)}\n```"
                except Exception:
                    msg += f"\n\n**Status:** {resp.status_code}\n{resp.text[:500]}"
            placeholder.markdown(msg)
            st.session_state.messages.append({"role": "assistant", "content": msg})

st.divider()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Query Mode", mode_label)
col2.metric("KB ID", kb_id or "—")
col3.metric("Model", model_id)
col4.metric("Documents", "MMT Invoices")

if st.button("🗑️ Clear Chat"):
    st.session_state.messages = []
    st.rerun()
