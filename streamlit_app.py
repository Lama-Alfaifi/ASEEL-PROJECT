from __future__ import annotations

import json
from pathlib import Path

import streamlit_app as st

from config.settings import VECTOR_DB_DIR
from workflow.graph import ask
from memory.conversation_memory import ConversationMemory
from utils.monitoring import (
    get_metrics,
    get_failure_patterns,
    load_runs,
)


st.set_page_config(
    page_title="ASEEL | Saudi Cultural Etiquette",
    page_icon="🌿",
    layout="centered",
)


st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        font-size: 12px;
    }

    [data-testid="stSidebar"] h1 {
        font-size: 18px;
        margin-bottom: 4px;
    }

    [data-testid="stSidebar"] h2 {
        font-size: 15px;
        margin-top: 6px;
        margin-bottom: 3px;
    }

    [data-testid="stSidebar"] h3 {
        font-size: 13px;
        margin-top: 5px;
        margin-bottom: 2px;
    }

    [data-testid="stSidebar"] p {
        font-size: 11px;
        margin-bottom: 2px;
    }

    [data-testid="stSidebar"] [data-testid="stMetric"] {
        padding: 0;
        margin: 0;
    }

    [data-testid="stSidebar"] [data-testid="stMetricLabel"] {
        font-size: 10px;
    }

    [data-testid="stSidebar"] [data-testid="stMetricValue"] {
        font-size: 16px;
    }

    [data-testid="stSidebar"] hr {
        margin: 7px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "messages" not in st.session_state:
    st.session_state.messages = []

if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()


st.title("ASEEL")

st.caption(
    "Saudi cultural etiquette guidance grounded only "
    "in the supplied regional knowledge base."
)


with st.sidebar:

    st.header("Monitoring")

    metrics = get_metrics()

    st.markdown(
        f"""
        **Requests:** {metrics['total_requests']}  
        **Successful:** {metrics['successful_requests']}  
        **Retries:** {metrics['retries']}  
        **Errors:** {metrics['errors']}  
        **Confidence:** {metrics['average_confidence']}  
        **Latency:** {metrics['average_latency']} sec
        """
    )

    patterns = get_failure_patterns()

    if patterns:
        st.subheader("Failures")
        st.json(patterns)
    else:
        st.caption("No failure patterns detected.")

    runs = load_runs()

    if runs:
        st.subheader("Recent Runs")

        recent = [
            {
                "Region": run.get(
                    "region",
                    "",
                ),
                "Confidence": run.get(
                    "confidence_score",
                    0,
                ),
                "Latency": run.get(
                    "latency_seconds",
                    0,
                ),
                "Status": run.get(
                    "status",
                    "",
                ),
            }
            for run in runs[-5:][::-1]
        ]

        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True,
        )

    if st.button(
        "Refresh",
        use_container_width=True,
    ):
        st.rerun()

    st.divider()

    st.subheader("DeepEval")

    deepeval_file = Path(
        "data/deepeval_results.json"
    )

    if deepeval_file.exists():

        try:
            with deepeval_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                deepeval = json.load(file)

            st.markdown(
                f"""
                **Tests:** {deepeval.get('test_cases', 0)}  
                **Relevancy:** {deepeval.get('answer_relevancy', 0):.2f}  
                **Faithfulness:** {deepeval.get('faithfulness', 0):.2f}  
                **Pass Rate:** {deepeval.get('answer_relevancy_pass_rate', 0):.0%}
                """
            )

            st.caption(
                f"Threshold: {deepeval.get('threshold', 0.7)}"
            )

        except Exception:
            st.warning(
                "Could not read DeepEval results."
            )

    else:
        st.caption(
            "No DeepEval results available yet."
        )

    st.divider()

    st.subheader("Memory")

    current_memory = (
        st.session_state.memory.get_context()
    )

    if current_memory:

        for key, value in current_memory.items():
            st.markdown(
                f"**{key}:** {value}"
            )

    else:
        st.caption(
            "No conversation context stored yet."
        )


for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):
        st.markdown(
            message["content"]
        )


left, right = st.columns([5, 1])

with right:

    if st.button(
        "Reset",
        use_container_width=True,
    ):
        st.session_state.messages = []
        st.session_state.memory = (
            ConversationMemory()
        )
        st.rerun()


prompt = st.chat_input(
    "Ask about a visit, meal, occasion, or regional custom…"
)


if prompt:

    if (
        not VECTOR_DB_DIR.exists()
        or not any(VECTOR_DB_DIR.iterdir())
    ):

        st.error(
            "Knowledge index not found. "
            "Add CSVs to data/raw and run "
            "`python scripts/build_index.py`."
        )

    else:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        history = "\n".join(
            f"{message['role']}: {message['content']}"
            for message
            in st.session_state.messages[-6:-1]
        )

        with st.chat_message("assistant"):

            with st.spinner(
                "ASEEL is understanding, retrieving, and validating…"
            ):

                try:

                    result = ask(
                        prompt,
                        history,
                        st.session_state.memory,
                    )

                except Exception as exc:

                    st.error(
                        f"ASEEL could not process that request: {exc}"
                    )

                    result = {
                        "answer": (
                            "Please confirm the knowledge index "
                            "is built and try again."
                        )
                    }

            answer = result.get(
                "answer",
                "No response was generated.",
            )

            st.markdown(answer)

            if result.get("sources"):

                with st.expander(
                    "Knowledge-base sources"
                ):

                    for source in result["sources"]:

                        st.write(
                            f"**{source['region']} · "
                            f"{source['category']}** — "
                            f"{source['question']}"
                        )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

