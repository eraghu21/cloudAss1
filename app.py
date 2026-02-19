import streamlit as st
import pandas as pd
import pyAesCrypt
import os
import json
import hashlib
import qrcode
from fpdf import FPDF
from datetime import datetime

# ================= CONFIG =================

PASSWORD = st.secrets["ENC_KEY"]
APP_URL = st.secrets["APP_URL"]
bufferSize = 64 * 1024

# ================= ENCRYPT / DECRYPT =================

def decrypt_file(enc_file, output_file):
    if os.path.exists(enc_file):
        pyAesCrypt.decryptFile(enc_file, output_file, PASSWORD, bufferSize)

def encrypt_progress():
    pyAesCrypt.encryptFile("progress.json", "progress.enc", PASSWORD, bufferSize)
    os.remove("progress.json")

# ================= LOAD STUDENTS =================

def load_students():
    decrypt_file("students.xlsx.enc", "students.xlsx")
    df = pd.read_excel("students.xlsx")
    df.columns = df.columns.str.strip()
    os.remove("students.xlsx")
    return df

# ================= LOAD QUESTIONS =================

def load_questions():
    decrypt_file("questions.xlsx.enc", "questions.xlsx")
    df = pd.read_excel("questions.xlsx")
    df.columns = df.columns.str.strip()
    os.remove("questions.xlsx")
    return df

# ================= LOAD PROGRESS =================

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

# ================= CERTIFICATE ID =================

def generate_cert_id(regno, score):
    raw = f"{regno}-{score}-SECUREKEY"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]

# ================= CERTIFICATE =================

def generate_certificate(student, score, total, cert_id):

    name = str(student.iloc[0])
    regno = str(student.iloc[1])
    dept = str(student.iloc[2])
    year = str(student.iloc[3])
    sec = str(student.iloc[4])

    file_name = f"{regno}_certificate.pdf"

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()

    # Background Image
    if os.path.exists("certificate_bg.png"):
        pdf.image("certificate_bg.png", x=0, y=0, w=297, h=210)

    # Name + Reg No
    pdf.set_font("Arial", "B", 18)
    pdf.set_xy(0, 100)
    pdf.cell(297, 10, f"{regno} ({name})", align="C")

    # Dept-Year-Sec
    pdf.set_font("Arial", "", 20)
    pdf.set_xy(0, 105)
    pdf.cell(297, 10, f"{dept} - {year} - {sec}", align="C")

    # Marks
    pdf.set_font("Arial", "B", 22)
    pdf.set_xy(0, 120)
    pdf.cell(297, 10, f" {score} / {total}", align="C")

    # Certificate ID
    pdf.set_font("Arial", "", 10)
    pdf.set_xy(10, 190)
    pdf.cell(100, 10, f"Certificate ID: {cert_id}")

    # Date
    pdf.set_xy(220, 190)
    pdf.cell(60, 10, datetime.today().strftime('%d-%m-%Y'), align="R")

    # QR Code
    qr_link = f"{APP_URL}?verify={cert_id}"
    qr = qrcode.make(qr_link)
    qr.save("qr.png")
    pdf.image("qr.png", x=250, y=150, w=30)
    os.remove("qr.png")

    pdf.output(file_name)
    return file_name

# ================= VERIFY MODE =================

query_params = st.query_params

if "verify" in query_params:
    cert_id = query_params["verify"]
    progress = load_progress()

    for reg, data in progress.items():
        if data["cert_id"] == cert_id:
            st.success("Certificate Verified ✅")
            st.write("Register No:", reg)
            st.write("Score:", data["score"], "/", data["total"])
            st.stop()

    st.error("Invalid Certificate ❌")
    st.stop()

# ================= MAIN APP =================

st.title("🎓 Secure Quiz & Certificate System")

students = load_students()
questions = load_questions()
progress = load_progress()

# Assume column order in students:
# 0=Name, 1=RegNo, 2=Dept, 3=Year, 4=Section

regno = st.text_input("Enter Register Number")

if st.button("Login"):

    student = students[students.iloc[:,1].astype(str) == regno]

    if student.empty:
        st.error("Invalid Register Number")
    else:
        st.session_state["student"] = student.iloc[0]
        st.success("Login Successful")

# ================= AFTER LOGIN =================

if "student" in st.session_state:

    student = st.session_state["student"]
    regno = str(student.iloc[1])

    st.success(f"Welcome {student.iloc[0]}")

    # Prevent Reattempt
    if regno in progress:

        st.warning("Quiz already completed")

        if st.button("Download Certificate"):

            cert_id = progress[regno]["cert_id"]
            file = generate_certificate(
                student,
                progress[regno]["score"],
                progress[regno]["total"],
                cert_id
            )

            with open(file, "rb") as f:
                st.download_button("Download Certificate", f, file_name=file)

    else:

        answers = []
        total = len(questions)

        # Assume question format:
        # 0=Question
        # 1=Option A
        # 2=Option B
        # 3=Option C
        # 4=Option D
        # 5=Correct Answer

        for i, row in questions.iterrows():

            st.write(f"Q{i+1}: {row.iloc[0]}")

            option = st.radio(
                "Select Answer",
                [
                    row.iloc[1],
                    row.iloc[2],
                    row.iloc[3],
                    row.iloc[4]
                ],
                key=i
            )

            answers.append(option)

        if st.button("Submit Quiz"):

            score = 0

            for i, row in questions.iterrows():
                if answers[i] == row.iloc[5]:
                    score += 1

            cert_id = generate_cert_id(regno, score)

            progress[regno] = {
                "score": score,
                "total": total,
                "cert_id": cert_id
            }

            save_progress(progress)

            st.success(f"Quiz Completed! Score: {score}/{total}")

            file = generate_certificate(student, score, total, cert_id)

            with open(file, "rb") as f:
                st.download_button("Download Certificate", f, file_name=file)
