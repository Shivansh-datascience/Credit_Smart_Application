import streamlit as st
import requests
import re

# ---------------- PAGE CONFIG -------------------
st.set_page_config(
    page_title="Policy RAG Chatbot",
    page_icon="💬",
    layout="wide"
)



st.title("📄 Policy RAG Chatbot")
st.markdown("""
<div style="
    background: white;
    padding: 20px 24px;
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.06);
    margin-bottom: 20px;
">
    <h1>📄 Policy RAG Chatbot</h1>
    <p style="color:#6b7280; margin-top:4px;">
        Ask questions related to Gold Loan, Interest Rate, KYC, Risk Management & other policies
    </p>
</div>
""", unsafe_allow_html=True)


# ---------------- SESSION STATE -------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- CLEAN RESPONSE -------------------
def clean_response(text: str) -> str:
    text = text.replace("\\n", " ").replace("\n", " ")
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ---------------- RENDER CHAT -------------------
def render_chat():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

render_chat()

def format_to_points(text: str) -> str:
    # Clean unwanted characters
    text = text.replace("\\n", " ").replace("\n", " ")
    text = text.replace("*", "")
    text = " ".join(text.split())

    # Split into logical sentences
    sentences = text.split(". ")

    # Convert to bullet points
    bullets = []
    for s in sentences:
        s = s.strip()
        if len(s) > 10:
            bullets.append(f"- {s.rstrip('.')}")
    
    return "\n".join(bullets)

# ---------------- USER INPUT -------------------
user_query = st.chat_input("Type your question here...")

if user_query:
    # 1️⃣ Show user message ONLY on frontend
    st.session_state.messages.append({
        "role": "user",
        "content": user_query
    })

    render_chat()

    # 2️⃣ Call backend (send query silently)
    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching policy documents… please wait"):
            try:
                response = requests.post(
                    "http://127.0.0.1:8001/api/chat",
                    json={"query": user_query},
                    timeout=200
                )

                if response.status_code == 200:
                    backend_answer = response.json().get("response", "")
                    final_answer = format_to_points(backend_answer)
                else:
                    final_answer = "❌ Unable to fetch response from server."

            except requests.exceptions.Timeout:
                final_answer = "⏳ Response is taking longer than expected. Please retry."
            except Exception as e:
                final_answer = f"❌ Error: {e}"

        st.markdown(final_answer)

    # 3️⃣ Store ONLY assistant answer (not user echo)
    st.session_state.messages.append({
        "role": "assistant",
        "content": final_answer
    })
