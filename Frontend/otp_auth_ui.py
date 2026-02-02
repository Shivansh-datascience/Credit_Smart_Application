import streamlit as st
import requests
import warnings 
warnings.filterwarnings(action="ignore") 


# ------------------ PAGE CONFIG ------------------
st.set_page_config(
    page_title="Credit Smart | OTP Login",
    page_icon="💳",
    layout="centered"
)

# ------------------ SESSION STATE ------------------
if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False
if "verified" not in st.session_state:
    st.session_state.verified = False

# ------------------ API URLs ------------------
GENERATE_OTP_URL = "http://127.0.0.1:8004/auth/Generate_OTP"
VERIFY_OTP_URL = "http://127.0.0.1:8004/auth/Verify_OTP"

# ------------------ CUSTOM STYLES ------------------
st.markdown("""
    <style>
    .main {
        background-color: #f5f7fa;
        color: #0f1115;
        font-family: 'Segoe UI', sans-serif;
    }
    .stButton>button {
        background-color: #0d6efd;
        color: white;
        font-weight: bold;
        height: 45px;
        border-radius: 8px;
    }
    .stTextInput>div>div>input {
        height: 40px;
        border-radius: 8px;
        border: 1px solid #ccc;
        padding-left: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.markdown("<h1 style='text-align:center; color:#0d6efd;'>💳 Credit Smart Application </h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center; color:#0d6efd;'>Secure OTP Login</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#6c757d;'>Fast and safe access to your finance dashboard</p>", unsafe_allow_html=True)
st.divider()

# ------------------ EMAIL INPUT ------------------
email = st.text_input("📧 Enter your Email", placeholder="example@email.com")

# ------------------ GENERATE OTP ------------------
if not st.session_state.otp_sent:
    if st.button("📨 Generate OTP", use_container_width=True):

        if not email:
            st.error("⚠️ Please enter your email address")
        else:
            payload = {"email_address": email}
            response = requests.post(GENERATE_OTP_URL, json=payload)

            if response.status_code == 200:
                st.success("✅ OTP sent to your email")
                st.session_state.otp_sent = True
            else:
                st.error("❌ Failed to generate OTP. Try again.")

# ------------------ OTP SECTION ------------------
if st.session_state.otp_sent and not st.session_state.verified:
    st.divider()
    st.markdown("<h4 style='color:#0d6efd;'>Enter the OTP received in your email</h4>", unsafe_allow_html=True)
    otp = st.text_input("🔢 OTP", max_chars=6, type="password", placeholder="6-digit code")

    col1, col2 = st.columns(2)

    # 🔄 Resend OTP
    with col1:
        if st.button("🔄 Resend OTP", use_container_width=True):
            payload = {"email_address": email}
            response = requests.post(GENERATE_OTP_URL, json=payload)

            if response.status_code == 200:
                st.success("✅ OTP resent successfully")
            else:
                st.error("❌ OTP resend failed")

    # ✅ Verify OTP
    with col2:
        if st.button("✅ Verify OTP", use_container_width=True):
            if not otp:
                st.error("⚠️ Please enter the OTP")
            else:
                payload = {"email_address": email, "user_otp": otp}
                response = requests.post(VERIFY_OTP_URL, json=payload)

                if response.status_code == 200:
                    st.success("🎉 OTP verified! Welcome to Credit Smart")
                    st.balloons()
                    st.session_state.verified = True
                else:
                    # Handle backend messages like "No otp found in session"
                    try:
                        message = response.json()[0].lower()
                        if "no otp found" in message:
                            st.warning("⚠️ No OTP found for this email. Please generate OTP first.")
                        elif "invalid otp" in message:
                            st.error("❌ Invalid OTP. Please try again.")
                        else:
                            st.info(f"ℹ️ {response.json()[0]}")
                    except:
                        st.error("❌ Unexpected server response")

# ------------------ DASHBOARD BUTTON ------------------
if st.session_state.verified:
    st.divider()
    st.markdown("<h4 style='color:#0d6efd;'>✅ Access your dashboard</h4>", unsafe_allow_html=True)
    if st.button("➡️ Go to Dashboard", use_container_width=True):
        # Navigate to dashboard page (if using multipage Streamlit app)
        st.experimental_set_query_params(page="dashboard")  # example for multipage navigation
        st.success("Redirecting to dashboard...")

# ------------------ FOOTER ------------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#6c757d;'>© 2026 Credit Smart Finance. All rights reserved.</p>", unsafe_allow_html=True)
