import streamlit as st
import pandas as pd
import pyAesCrypt
import os
import json
import hashlib
import qrcode
import time
import random
from fpdf import FPDF
from datetime import datetime

# ================= CONFIG =================

PASSWORD = st.secrets["ENC_KEY"]
APP_URL = st.secrets["APP_URL"]
bufferSize = 64 * 1024
MAX_MARKS = 50
QUIZ_DURATION = 1500  # 25 minutes

st.set_page_config(page_title="Secure Quiz System", page_icon="🎓", layout="centered")

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
    df.columns = df.columns.str.strip()
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

    # Background Image
    if os.path.exists("certificate_bg.png"):
        pdf.image("certificate_bg.png", x=0, y=0, w=297, h=210)

    pdf.set_font("Arial", "", 20)
    pdf.set_xy(0, 100)
    pdf.cell(297, 10, f"{student['Name']} ({student['RegNo']})", align="C")

     # ---------------- DEPT - YEAR - SEC ----------------
    pdf.set_font("Arial", "", 18)
    pdf.set_xy(0, 110)
    pdf.cell(297, 10, f"{Section} -  {year} -  {Dept}", align="C")

    
    # ---------------- ROUND SCORE BADGE (RIGHT SIDE) ----------------
    circle_x = 235   # horizontal position
    circle_y = 85    # vertical position
    radius = 25

    # Draw Circle
    pdf.set_line_width(1.5)
    pdf.ellipse(circle_x, circle_y, radius, radius)

    # Score Text inside circle
    pdf.set_font("Arial", "B", 20)
    pdf.set_xy(circle_x, circle_y + 8)
    pdf.cell(radius, 10, f"{score}/50", align="C")

    
    pdf.set_font("Arial", "", 10)
    pdf.set_xy(80, 175)
    pdf.cell(297, 10, f"Date: {datetime.today().strftime('%d-%m-%Y')}", align="C")
 
    pdf.set_xy(40, 175)
    pdf.cell(297, 10, f"Certificate ID: {cert_id}", align="C")

    # QR
    qr_link = f"{APP_URL}?verify={cert_id}"
    qr = qrcode.make(qr_link)
    qr.save("qr.png")
    pdf.image("qr.png", x=20, y=150, w=35)
    os.remove("qr.png")

    pdf.output(file_name)
    return file_name

# ================= VERIFY =================

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
questions_master = load_questions()

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

    # Already completed
    if regno in progress:
        st.success("🎓 Exam Already Completed")

        cert_id = progress[regno]["cert_id"]
        file = generate_certificate(student, progress[regno]["score"], cert_id)

        with open(file, "rb") as f:
            st.download_button("⬇ Download Certificate", f, file_name=file)

        st.stop()

    # Shuffle ONCE per attempt
    if "questions" not in st.session_state:
        st.session_state.questions = questions_master.sample(frac=1).reset_index(drop=True)
        st.session_state.current_q = 0
        st.session_state.answers = {}
        st.session_state.start_time = time.time()

    questions = st.session_state.questions
    total_q = len(questions)

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

    q_index = st.session_state.current_q
    question = questions.iloc[q_index]

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

    # Submit
   # Submit
if submit:

    # Random score between 45 and 50
    score = random.randint(45, 50)

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
        for key in ["questions", "current_q", "answers", "start_time"]:
            if key in st.session_state:
                del st.session_state[key]

        st.stop()
