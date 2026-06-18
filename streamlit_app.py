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
st.title("🧾 MakeMyTrip Invoice RAG")
st.caption("Provision infrastructure once, then chat with your travel invoices")

# ---------- session state defaults ----------
for key in ("bucket_name", "collection_arn", "collection_id",
            "kb_id", "ds_id", "job_id", "setup_done"):
    if key not in st.session_state:
        st.session_state[key] = ""

_default_kb_id = os.getenv("KNOWLEDGE_BASE_ID", "")
if not _default_kb_id:
    try:
        with open(KB_CONFIG_PATH) as f:
            _default_kb_id = json.load(f).get("kb_id", "")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

with st.sidebar:
    st.header("Connection")
    api_url = st.text_input("Flask API URL", value=API_BASE)

    st.divider()
    st.caption("Health & Info")
    if st.button("🩺 Health Check"):
        try:
            r = requests.get(f"{api_url}/health", timeout=5)
            r.raise_for_status()
            st.success(f"Server OK — {r.json()}")
        except Exception as e:
            st.error(f"Server unreachable: {e}")

    if st.button("📋 List KBs"):
        try:
            r = requests.get(f"{api_url}/api/v1/kb/list", timeout=10)
            r.raise_for_status()
            for kb in r.json().get("knowledge_bases", []):
                st.code(f"{kb['name']} — {kb['knowledgeBaseId']}")
        except Exception as e:
            st.error(f"Failed: {e}")

tab_setup, tab_chat = st.tabs(["🔧 Setup Infrastructure", "💬 Chat with Invoices"])

# =============================================================
# TAB 1 — ONE-TIME SETUP
# =============================================================
with tab_setup:
    st.subheader("Infrastructure Provisioning")
    st.info("Run these steps in order — outputs from each step feed into the next. Backend is idempotent — already-created resources will be reused.")

    c1, c2 = st.columns([1, 2])

    # -- Step 1: S3 Bucket --
    with c1:
        if st.button("1️⃣ Create S3 Bucket", use_container_width=True):
            with st.spinner("Creating bucket..."):
                try:
                    r = requests.post(f"{api_url}/api/v1/kb/create-bucket",
                                      json={"bucket_name": "mmt-invoices"}, timeout=30)
                    r.raise_for_status()
                    data = r.json()
                    st.session_state.bucket_name = data["bucket"]
                    st.success(f"Bucket `{data['bucket']}` created in {data['region']}")
                except Exception as e:
                    st.error(f"Failed: {e}")
    with c2:
        if st.session_state.bucket_name:
            st.code(st.session_state.bucket_name)
        else:
            st.caption("Awaiting creation")

    # -- Step 2: Download documents --
    with c1:
        if st.button("2️⃣ Download Sample Docs", use_container_width=True):
            with st.spinner("Downloading..."):
                try:
                    r = requests.post(f"{api_url}/api/v1/kb/download-documents",
                                      json={"data_dir": "./data"}, timeout=30)
                    r.raise_for_status()
                    data = r.json()
                    st.success(f"{len(data['files'])} files downloaded to `./data/`")
                except Exception as e:
                    st.error(f"Failed: {e}")

    # -- Step 3: Upload to S3 --
    with c1:
        bucket_ok = bool(st.session_state.bucket_name)
        btn3 = st.button("3️⃣ Upload Docs to S3", disabled=not bucket_ok, use_container_width=True)
        if btn3:
            with st.spinner("Uploading..."):
                try:
                    r = requests.post(f"{api_url}/api/v1/kb/upload-to-s3",
                                      json={"local_path": "./data", "bucket_name": st.session_state.bucket_name},
                                      timeout=120)
                    r.raise_for_status()
                    data = r.json()
                    st.success(f"{len(data['files'])} files uploaded to `{st.session_state.bucket_name}`")
                except Exception as e:
                    st.error(f"Failed: {e}")
    with c2:
        if bucket_ok:
            st.code(st.session_state.bucket_name)
        else:
            st.caption("Run step 1 first")

    # -- Step 4: OpenSearch Collection --
    with c1:
        if st.button("4️⃣ Create OSS Collection", use_container_width=True):
            with st.spinner("Creating collection (takes ~30s)..."):
                try:
                    r = requests.post(f"{api_url}/api/v1/kb/create-collection",
                                      json={}, timeout=90)
                    r.raise_for_status()
                    data = r.json()
                    st.session_state.collection_arn = data["collection_arn"]
                    st.session_state.collection_id = data["collection_id"]
                    st.success(f"Collection `{data['collection_name']}` created")
                except Exception as e:
                    st.error(f"Failed: {e}")
    with c2:
        parts = []
        if st.session_state.collection_id:
            parts.append(f"ID: `{st.session_state.collection_id}`")
        if st.session_state.collection_arn:
            parts.append(f"ARN: `{st.session_state.collection_arn}`")
        if parts:
            st.code("\n".join(parts))
        else:
            st.caption("Awaiting creation")

    # -- Step 5: Create Knowledge Base --
    with c1:
        coll_ok = bool(st.session_state.collection_arn and st.session_state.collection_id and st.session_state.bucket_name)
        btn5 = st.button("5️⃣ Create Knowledge Base", disabled=not coll_ok, use_container_width=True)
        if btn5:
            with st.spinner("Creating KB..."):
                try:
                    r = requests.post(f"{api_url}/api/v1/kb/create",
                                      json={
                                          "bucket_name": st.session_state.bucket_name,
                                          "collection_arn": st.session_state.collection_arn,
                                          "collection_id": st.session_state.collection_id,
                                      }, timeout=120)
                    r.raise_for_status()
                    data = r.json()
                    st.session_state.kb_id = data["kb_id"]
                    st.success(f"KB `{data['kb_id']}` created")
                except Exception as e:
                    st.error(f"Failed: {e}")
    with c2:
        if st.session_state.kb_id:
            st.code(st.session_state.kb_id)
        else:
            st.caption("Run steps 1 & 4 first")

    # -- Step 6: Create Data Source --
    with c1:
        kb_ok = bool(st.session_state.kb_id and st.session_state.bucket_name)
        btn6 = st.button("6️⃣ Create Data Source", disabled=not kb_ok, use_container_width=True)
        if btn6:
            with st.spinner("Creating data source..."):
                try:
                    r = requests.post(f"{api_url}/api/v1/kb/create-data-source",
                                      json={
                                          "kb_id": st.session_state.kb_id,
                                          "bucket_name": st.session_state.bucket_name,
                                      }, timeout=30)
                    r.raise_for_status()
                    data = r.json()
                    st.session_state.ds_id = data["data_source_id"]
                    st.success(f"Data source `{data['data_source_id']}` created")
                except Exception as e:
                    st.error(f"Failed: {e}")
    with c2:
        if st.session_state.ds_id:
            st.code(st.session_state.ds_id)
        else:
            st.caption("Run step 5 first")

    # -- Step 7: Start Ingestion --
    with c1:
        ds_ok = bool(st.session_state.kb_id and st.session_state.ds_id)
        btn7 = st.button("7️⃣ Start Ingestion Job", disabled=not ds_ok, use_container_width=True)
        if btn7:
            with st.spinner("Starting ingestion..."):
                try:
                    r = requests.post(f"{api_url}/api/v1/kb/start-ingestion",
                                      json={
                                          "kb_id": st.session_state.kb_id,
                                          "ds_id": st.session_state.ds_id,
                                      }, timeout=30)
                    r.raise_for_status()
                    data = r.json()
                    st.session_state.job_id = data["job_id"]
                    st.session_state.setup_done = True
                    st.success(f"Ingestion job `{data['job_id']}` started")
                except Exception as e:
                    st.error(f"Failed: {e}")

    # -- Ingestion Status --
    if st.session_state.job_id:
        st.divider()
        st.subheader("Ingestion Status")
        if st.button("🔄 Check Ingestion Status"):
            try:
                r = requests.get(f"{api_url}/api/v1/kb/ingestion-status",
                                 params={
                                     "kb_id": st.session_state.kb_id,
                                     "ds_id": st.session_state.ds_id,
                                     "job_id": st.session_state.job_id,
                                 }, timeout=10)
                r.raise_for_status()
                status = r.json().get("status", "UNKNOWN")
                if status == "COMPLETE":
                    st.success(f"Status: {status}")
                elif status in ("FAILED", "STOPPED"):
                    st.error(f"Status: {status}")
                else:
                    st.info(f"Status: {status} — ingestion in progress (this may take several minutes)")
            except Exception as e:
                st.error(f"Failed: {e}")

    # -- Quick recap of stored values --
    if st.session_state.kb_id:
        st.divider()
        st.caption("Provisioned resources")
        recap = {
            "Bucket": st.session_state.bucket_name,
            "KB ID": st.session_state.kb_id,
            "Data Source ID": st.session_state.ds_id,
            "Ingestion Job ID": st.session_state.job_id,
        }
        for label, val in recap.items():
            if val:
                st.code(f"{label}: {val}")

# =============================================================
# TAB 2 — CHAT
# =============================================================
with tab_chat:
    kb_id = st.text_input("Knowledge Base ID", value=st.session_state.kb_id or _default_kb_id,
                          help="Auto-filled from setup, or paste your KB ID")

    col_mode, col_adv = st.columns([1, 1])
    with col_mode:
        mode_label = st.selectbox("Query Mode", list(QUERY_MODES.keys()))
    with col_adv:
        with st.expander("Advanced"):
            num_results = st.number_input("Number of Results", min_value=1, max_value=50, value=5)
            model_id = st.text_input("Model ID", value="amazon.nova-lite-v1:0")
            search_type = st.selectbox("Search Type", ["SEMANTIC", "HYBRID"], index=0)

    endpoint = QUERY_MODES[mode_label]

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

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Query Mode", mode_label)
    col2.metric("KB ID", kb_id or "—")
    col3.metric("Model", model_id)
    col4.metric("Documents", "MMT Invoices")

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()
