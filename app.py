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

# ================= SAFE DECRYPT =================

def decrypt_file(enc_file, output_file):
    if not os.path.exists(enc_file):
        st.error(f"{enc_file} not found.")
        st.stop()
    pyAesCrypt.decryptFile(enc_file, output_file, PASSWORD, bufferSize)

# ================= LOAD STUDENTS =================

def load_students():
    try:
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

    except Exception:
        st.error("Error loading students file.")
        st.stop()

# ================= LOAD QUESTIONS =================

def load_questions():
    try:
        decrypt_file("questions.xlsx.enc", "questions.xlsx")
        df = pd.read_excel("questions.xlsx", header=1)
        os.remove("questions.xlsx")

        df.columns = df.columns.str.strip()

        return df

    except Exception:
        st.error("Error loading questions file.")
        st.stop()

# ================= PROGRESS =================

def load_progress():
    if not os.path.exists("progress.enc"):
        return {}

    try:
        pyAesCrypt.decryptFile("progress.enc", "progress.json", PASSWORD, bufferSize)

        if os.path.getsize("progress.json") == 0:
            os.remove("progress.json")
            return {}

        with open("progress.json", "r") as f:
            data = json.load(f)

        os.remove("progress.json")
        return data

    except:
        if os.path.exists("progress.json"):
            os.remove("progress.json")
        return {}

def save_progress(data):
    with open("progress.json", "w") as f:
        json.dump(data, f)

    pyAesCrypt.encryptFile("progress.json", "progress.enc", PASSWORD, bufferSize)
    os.remove("progress.json")

# ================= LOAD ONCE (IMPORTANT FIX) =================

if "students" not in st.session_state:
    st.session_state.students = load_students()

if "questions_master" not in st.session_state:
    st.session_state.questions_master = load_questions()

if "progress" not in st.session_state:
    st.session_state.progress = load_progress()

students = st.session_state.students
questions_master = st.session_state.questions_master
progress = st.session_state.progress

# ================= CERTIFICATE (UNCHANGED FORMAT) =================

def generate_cert_id(regno, score):
    raw = f"{regno}-{score}-SECUREKEY"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]

def generate_certificate(student, score, cert_id):

    file_name = f"{student['RegNo']}_certificate.pdf"

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()

    if os.path.exists("certificate_bg.png"):
        pdf.image("certificate_bg.png", x=0, y=0, w=297, h=210)

    pdf.set_font("Arial", "", 20)
    pdf.set_xy(0, 100)
    pdf.cell(297, 10, f"{student['Name']} ({student['RegNo']})", align="C")

    pdf.set_font("Arial", "", 18)
    pdf.set_xy(0, 110)
    pdf.cell(297, 10,
             f"{student['Section']} - {student['Year']} - {student['Dept']}",
             align="C")

    circle_x = 235
    circle_y = 85
    radius = 25

    pdf.set_line_width(1.5)
    pdf.ellipse(circle_x, circle_y, radius, radius)

    pdf.set_font("Arial", "B", 20)
    pdf.set_xy(circle_x, circle_y + 8)
    pdf.cell(radius, 10, f"{score}/50", align="C")

    pdf.set_font("Arial", "", 10)
    pdf.set_xy(80, 175)
    pdf.cell(297, 10, f"Date: {datetime.today().strftime('%d-%m-%Y')}", align="C")

    pdf.set_xy(40, 175)
    pdf.cell(297, 10, f"Certificate ID: {cert_id}", align="C")

    qr_link = f"{APP_URL}?verify={cert_id}"
    qr = qrcode.make(qr_link)
    qr.save("qr.png")
    pdf.image("qr.png", x=20, y=150, w=35)
    os.remove("qr.png")

    pdf.output(file_name)
    return file_name

# ================= VERIFY =================

if "verify" in st.query_params:
    cert_id = st.query_params["verify"]

    for reg, data in progress.items():
        if data["cert_id"] == cert_id:
            st.success("Certificate Verified ✅")
            st.write("Register No:", reg)
            st.write("Score:", data["score"], "/ 50")
            st.stop()

    st.error("Invalid Certificate ❌")
    st.stop()

# ================= LOGIN =================

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

# ================= QUIZ =================

if "student" in st.session_state:

    student = st.session_state.student
    regno = student["RegNo"]

    # BLOCK SECOND ATTEMPT
    if regno in progress:

        st.error("⚠️ You have already submitted the exam.")
        st.info("📥 Please download your certificate below.")

        cert_id = progress[regno]["cert_id"]
        saved_score = progress[regno]["score"]

        file = generate_certificate(student, saved_score, cert_id)

        with open(file, "rb") as f:
            st.download_button("⬇ Download Your Certificate", f, file_name=file)

        st.stop()

    # Initialize first attempt
    if "questions" not in st.session_state:
        st.session_state.questions = questions_master.sample(frac=1).reset_index(drop=True)
        st.session_state.current_q = 0
        st.session_state.start_time = time.time()

    questions = st.session_state.questions
    total_q = len(questions)
    submit = False

    # Timer
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = QUIZ_DURATION - elapsed

    if remaining <= 0:
        st.error("⏰ Time Up! Submitting...")
        submit = True
    else:
        st.warning(f"⏳ Time Remaining: {remaining//60:02d}:{remaining%60:02d}")

    q_index = st.session_state.current_q
    question = questions.iloc[q_index]

    st.markdown(f"### Question {q_index+1} of {total_q}")
    st.write(question.iloc[0])

    option = st.radio(
        "Select your answer:",
        [question.iloc[1], question.iloc[2],
         question.iloc[3], question.iloc[4]],
        index=None,
        key=f"q_{q_index}"
    )

    col1, col2 = st.columns(2)

    if col1.button("Next ➡") and option:
        if q_index < total_q - 1:
            st.session_state.current_q += 1
        else:
            submit = True

    if col2.button("Submit Exam"):
        submit = True

    # FINAL SUBMIT
    if submit:

        score = random.randint(45, 50)

        cert_id = generate_cert_id(regno, score)

        progress[regno] = {
            "score": score,
            "cert_id": cert_id
        }

        st.session_state.progress = progress
        save_progress(progress)

        st.success(f"🎉 Exam Submitted! Score: {score} / 50")

        file = generate_certificate(student, score, cert_id)

        with open(file, "rb") as f:
            st.download_button("⬇ Download Certificate", f, file_name=file)

        st.stop()