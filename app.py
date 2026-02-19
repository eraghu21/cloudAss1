import streamlit as st
import pandas as pd
import pyAesCrypt
import os
import json
import hashlib
import qrcode
from fpdf import FPDF
from datetime import datetime

# ---------------- CONFIG ----------------

PASSWORD = st.secrets["ENC_KEY"]
APP_URL = st.secrets["APP_URL"]
bufferSize = 64 * 1024

# ---------------- ENCRYPT / DECRYPT ----------------

def decrypt_file(enc_file, output_file):
    if os.path.exists(enc_file):
        pyAesCrypt.decryptFile(enc_file, output_file, PASSWORD, bufferSize)

def encrypt_progress():
    pyAesCrypt.encryptFile("progress.json", "progress.enc", PASSWORD, bufferSize)
    os.remove("progress.json")

# ---------------- LOAD STUDENTS ----------------

def load_students():
    decrypt_file("students.xlsx.enc", "students.xlsx")
    df = pd.read_excel("students.xlsx", header=1)
    df.columns = df.columns.str.strip().str.lower()
    os.remove("students.xlsx")
    return df

# ---------------- LOAD QUESTIONS ----------------

def load_questions():
    decrypt_file("questions.xlsx.enc", "questions.xlsx")
    df = pd.read_excel("questions.xlsx", header=1)
    df.columns = df.columns.str.strip().str.lower()
    os.remove("questions.xlsx")
    return df

# ---------------- LOAD PROGRESS ----------------

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

# ---------------- COLUMN FINDER ----------------

def find_column(df, keywords):
    for col in df.columns:
        for key in keywords:
            if key in col:
                return col
    return None

# ---------------- CERTIFICATE ID ----------------

def generate_cert_id(regno, score):
    raw = f"{regno}-{score}-SECUREKEY"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]

# ---------------- CERTIFICATE ----------------

def generate_certificate(student, score, total, cert_id,
                         name_col, reg_col, dept_col, year_col, sec_col):

    file_name = f"{student[reg_col]}_certificate.pdf"

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()

    if os.path.exists("certificate_bg.png"):
        pdf.image("certificate_bg.png", x=0, y=0, w=297, h=210)

    pdf.set_font("Arial", "B", 28)
    pdf.set_xy(0, 90)
    pdf.cell(297, 10,
             f"{student[name_col]} ({student[reg_col]})",
             align="C")

    pdf.set_font("Arial", "", 18)
    pdf.set_xy(0, 110)
    pdf.cell(297, 10,
             f"{student[dept_col]} - Year {student[year_col]} - Section {student[sec_col]}",
             align="C")

    pdf.set_font("Arial", "B", 20)
    pdf.set_xy(0, 135)
    pdf.cell(297, 10,
             f"Marks Obtained: {score} / {total}",
             align="C")

    pdf.set_font("Arial", "", 10)
    pdf.set_xy(10, 190)
    pdf.cell(100, 10, f"Certificate ID: {cert_id}")

    pdf.set_xy(220, 190)
    pdf.cell(60, 10,
             f"Date: {datetime.today().strftime('%d-%m-%Y')}",
             align="R")

    qr_link = f"{APP_URL}?verify={cert_id}"
    qr = qrcode.make(qr_link)
    qr.save("qr.png")
    pdf.image("qr.png", x=250, y=150, w=30)
    os.remove("qr.png")

    pdf.output(file_name)
    return file_name

# ---------------- VERIFY PAGE ----------------

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

# ---------------- MAIN APP ----------------

st.title("🎓 Secure Online Quiz & Certificate System")

students = load_students()
questions = load_questions()
progress = load_progress()

# Detect student columns automatically
name_col = find_column(students, ["name"])
reg_col = find_column(students, ["reg"])
dept_col = find_column(students, ["dept"])
year_col = find_column(students, ["year"])
sec_col = find_column(students, ["sec"])

if not reg_col:
    st.error("Register column not found in Students Excel.")
    st.write("Detected columns:", students.columns.tolist())
    st.stop()

# Detect question columns automatically
q_col = find_column(questions, ["question"])
opt_a_col = find_column(questions, ["option a", "optiona"])
opt_b_col = find_column(questions, ["option b", "optionb"])
opt_c_col = find_column(questions, ["option c", "optionc"])
opt_d_col = find_column(questions, ["option d", "optiond"])
correct_col = find_column(questions, ["correct"])

regno = st.text_input("Enter Register Number")

if st.button("Login"):
    student = students[students[reg_col].astype(str) == regno]

    if student.empty:
        st.error("Invalid Register Number")
    else:
        st.session_state["student"] = student.iloc[0]

if "student" in st.session_state:

    student = st.session_state["student"]
    st.success(f"Welcome {student[name_col]}")

    if regno in progress:
        st.warning("Quiz already completed!")

        if st.button("Download Certificate"):
            cert_id = progress[regno]["cert_id"]
            file = generate_certificate(
                student,
                progress[regno]["score"],
                progress[regno]["total"],
                cert_id,
                name_col, reg_col, dept_col, year_col, sec_col
            )

            with open(file, "rb") as f:
                st.download_button("Download Certificate", f, file_name=file)

    else:
        answers = []
        total = len(questions)

        for i, row in questions.iterrows():
            st.write(f"Q{i+1}: {row[q_col]}")

            option = st.radio(
                "Select Answer",
                [row[opt_a_col], row[opt_b_col],
                 row[opt_c_col], row[opt_d_col]],
                key=i
            )

            answers.append(option)

        if st.button("Submit Quiz"):
            score = 0
            for i, row in questions.iterrows():
                if answers[i] == row[correct_col]:
                    score += 1

            cert_id = generate_cert_id(regno, score)

            progress[regno] = {
                "score": score,
                "total": total,
                "cert_id": cert_id
            }

            save_progress(progress)

            st.success(f"Quiz Completed! Score: {score}/{total}")

            file = generate_certificate(
                student, score, total, cert_id,
                name_col, reg_col, dept_col, year_col, sec_col
            )

            with open(file, "rb") as f:
                st.download_button("Download Certificate", f, file_name=file)
