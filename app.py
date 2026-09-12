from __future__ import annotations
import streamlit as st
from config.settings import VECTOR_DB_DIR
from workflow.graph import ask

st.set_page_config(page_title="ASEEL | Saudi Cultural Etiquette", page_icon="🌿", layout="centered")
st.title("ASEEL")
st.caption("Saudi cultural etiquette guidance grounded only in the supplied regional knowledge base.")

if "messages" not in st.session_state:
    st.session_state.messages = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

left, right = st.columns([5, 1])
with right:
    if st.button("Reset", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

prompt = st.chat_input("Ask about a visit, meal, occasion, or regional custom…")
if prompt:
    if not VECTOR_DB_DIR.exists() or not any(VECTOR_DB_DIR.iterdir()):
        st.error("Knowledge index not found. Add CSVs to data/raw and run `python scripts/build_index.py`.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        history = "\n".join(f"{m['role']}: {m['content']}" for m in st.session_state.messages[-6:-1])
        with st.chat_message("assistant"):
            with st.spinner("ASEEL is understanding, retrieving, and validating…"):
                try:
                    result = ask(prompt, history)
                except Exception as exc:
                    st.error(f"ASEEL could not process that request: {exc}")
                    result = {"answer": "Please confirm the knowledge index is built and try again."}
            st.markdown(result["answer"])
            if result.get("sources"):
                with st.expander("Knowledge-base sources"):
                    for source in result["sources"]:
                        st.write(f"**{source['region']} · {source['category']}** — {source['question']}")
        st.session_state.messages.append({"role": "assistant", "content": result["answer"]})