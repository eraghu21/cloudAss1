import streamlit as st
import pandas as pd
import pyAesCrypt
import os
import json
import hashlib
import qrcode
import random
import time
from fpdf import FPDF
from datetime import datetime

# ================= CONFIG =================

PASSWORD = st.secrets["ENC_KEY"]
APP_URL = st.secrets["APP_URL"]
bufferSize = 64 * 1024
MAX_MARKS = 50
QUIZ_DURATION = 300  # 5 minutes

st.set_page_config(page_title="Secure Quiz System", page_icon="🎓", layout="centered")

# ================= UI =================

st.markdown("""
<style>
.main { background-color: #f4f6f9; }
.quiz-card {
    background: white;
    padding: 25px;
    border-radius: 12px;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.08);
}
.stButton>button {
    background-color: #1f4e79;
    color: white;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

st.title("🎓 Cloud Basics & Infrastructure Quiz")

# ================= ENCRYPT/DECRYPT =================

def decrypt_file(enc_file, output_file):
    pyAesCrypt.decryptFile(enc_file, output_file, PASSWORD, bufferSize)

def encrypt_progress():
    pyAesCrypt.encryptFile("progress.json", "progress.enc", PASSWORD, bufferSize)
    os.remove("progress.json")

# ================= LOAD DATA =================

def load_students():
    decrypt_file("students.xlsx.enc", "students.xlsx")
    df = pd.read_excel("students.xlsx", header=1)
    os.remove("students.xlsx")

    df.columns = df.columns.str.strip()

    df = df.rename(columns={
        df.columns[0]: "RegNo",
        df.columns[1]: "Name",
        df.columns[2]: "Dept",
        df.columns[3]: "Year",
        df.columns[4]: "Section"
    })

    df["RegNo"] = df["RegNo"].astype(str).str.replace(".0", "", regex=False).str.strip()
    return df

def load_questions():
    decrypt_file("questions.xlsx.enc", "questions.xlsx")
    df = pd.read_excel("questions.xlsx", header=1)
    os.remove("questions.xlsx")

    df = df.sample(frac=1).reset_index(drop=True)  # Shuffle
    return df

def load_progress():
    if os.path.exists("progress.enc"):
        pyAesCrypt.decryptFile("progress.enc", "progress.json", PASSWORD, bufferSize)
        with open("progress.json", "r") as f:
            data = json.load(f)
        os.remove("progress.json")
        return data
    return {}

def save_progress(data):
    with open("progress.json", "w") as f:
        json.dump(data, f)
    encrypt_progress()

# ================= CERTIFICATE =================

def generate_cert_id(regno, score):
    raw = f"{regno}-{score}-SECUREKEY"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]

def generate_certificate(student, score, cert_id):
    file_name = f"{student['RegNo']}_certificate.pdf"
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()

    pdf.set_font("Arial", "B", 24)
    pdf.cell(0, 30, "CERTIFICATE OF COMPLETION", ln=True, align="C")

    pdf.set_font("Arial", "", 18)
    pdf.cell(0, 20, f"{student['Name']} ({student['RegNo']})", ln=True, align="C")
    pdf.cell(0, 15, f"Score: {score} / 50", ln=True, align="C")

    pdf.cell(0, 15, f"Date: {datetime.today().strftime('%d-%m-%Y')}", ln=True, align="C")
    pdf.cell(0, 15, f"Certificate ID: {cert_id}", ln=True, align="C")

    qr_link = f"{APP_URL}?verify={cert_id}"
    qr = qrcode.make(qr_link)
    qr.save("qr.png")
    pdf.image("qr.png", x=130, y=120, w=40)
    os.remove("qr.png")

    pdf.output(file_name)
    return file_name

# ================= VERIFY MODE =================

query_params = st.query_params
progress = load_progress()

if "verify" in query_params:
    cert_id = query_params["verify"]
    for reg, data in progress.items():
        if data["cert_id"] == cert_id:
            st.success("Certificate Verified ✅")
            st.write("Register No:", reg)
            st.write("Score:", data["score"], "/ 50")
            st.stop()
    st.error("Invalid Certificate ❌")
    st.stop()

# ================= LOGIN =================

students = load_students()
questions = load_questions()

st.subheader("🔐 Student Login")
reg_input = st.text_input("Enter Register Number")

if st.button("Login"):
    reg_clean = reg_input.strip().replace(".0", "")
    student_df = students[students["RegNo"] == reg_clean]

    if student_df.empty:
        st.error("Invalid Register Number")
    else:
        st.session_state.student = student_df.iloc[0].to_dict()
        st.success("Login Successful")

# ================= AFTER LOGIN =================

if "student" in st.session_state:

    student = st.session_state.student
    regno = student["RegNo"]

    # If already attempted
    if regno in progress:
        st.success("🎓 Exam Already Completed")

        cert_id = progress[regno]["cert_id"]
        file = generate_certificate(student, progress[regno]["score"], cert_id)

        with open(file, "rb") as f:
            st.download_button("⬇ Download Certificate", f, file_name=file)

        st.stop()

    # Initialize quiz state
    if "current_q" not in st.session_state:
        st.session_state.current_q = 0
        st.session_state.answers = {}
        st.session_state.start_time = time.time()

    # Timer
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = QUIZ_DURATION - elapsed

    if remaining <= 0:
        st.error("⏰ Time Up! Submitting...")
        submit = True
    else:
        mins = remaining // 60
        secs = remaining % 60
        st.warning(f"⏳ Time Remaining: {mins:02d}:{secs:02d}")
        submit = False

    total_q = len(questions)
    q_index = st.session_state.current_q
    question = questions.iloc[q_index]

    st.markdown('<div class="quiz-card">', unsafe_allow_html=True)
    st.markdown(f"### Question {q_index+1} of {total_q}")
    st.write(question.iloc[0])

    option = st.radio(
        "Select your answer:",
        [
            question.iloc[1],
            question.iloc[2],
            question.iloc[3],
            question.iloc[4]
        ],
        index=None,
        key=f"q_{q_index}"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    if col1.button("Next ➡") and option:
        st.session_state.answers[q_index] = option
        if q_index < total_q - 1:
            st.session_state.current_q += 1
        else:
            submit = True

    if col2.button("Submit Exam"):
        if option:
            st.session_state.answers[q_index] = option
        submit = True

    # Submit Logic
    if submit:
        correct = 0
        for i in range(total_q):
            if i in st.session_state.answers:
                if st.session_state.answers[i] == questions.iloc[i].iloc[5]:
                    correct += 1

        score = round((correct / total_q) * MAX_MARKS)
        cert_id = generate_cert_id(regno, score)

        progress[regno] = {
            "score": score,
            "cert_id": cert_id
        }

        save_progress(progress)

        st.success(f"🎉 Exam Submitted! Score: {score} / 50")

        file = generate_certificate(student, score, cert_id)

        with open(file, "rb") as f:
            st.download_button("⬇ Download Certificate", f, file_name=file)

        # Clear session
        for key in ["current_q", "answers", "start_time"]:
            if key in st.session_state:
                del st.session_state[key]

        st.stop()
