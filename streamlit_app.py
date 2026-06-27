import os

import streamlit as st
import requests

API_BASE = os.getenv("FLASK_API_URL", "http://localhost:5000")
ENDPOINT = "/api/v1/rag/generate"

_default_kb_id = os.getenv("KNOWLEDGE_BASE_ID", "")

st.set_page_config(page_title="MMT Invoice RAG", page_icon="🧾")
st.title("🧾 MakeMyTrip Invoice Query")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

with st.expander("💡 Example questions"):
    st.markdown("""
    - How much did I spend on train tickets last month?
    - What is the total amount of my cancelled bookings?
    - List all my trips from London to Edinburgh
    - Show me refunds processed in March
    - Which booking has the highest fare?
    """)

if query := st.chat_input("Ask a question about your MakeMyTrip invoices..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    payload = {"query": query}
    if _default_kb_id:
        payload["kb_id"] = _default_kb_id

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳ Thinking...")

        try:
            resp = requests.post(f"{API_BASE}{ENDPOINT}", json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("answer", data.get("output", {}).get("text", str(data)))
            placeholder.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except requests.exceptions.Timeout:
            placeholder.markdown("❌ Request timed out.")
            st.session_state.messages.append({"role": "assistant", "content": "❌ Request timed out."})
        except requests.exceptions.ConnectionError:
            placeholder.markdown(f"❌ Cannot connect to `{API_BASE}`. Is the Flask server running?")
            st.session_state.messages.append({"role": "assistant", "content": f"❌ Cannot connect to {API_BASE}."})
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

if st.button("🗑️ Clear Chat"):
    st.session_state.messages = []
    st.rerun()
