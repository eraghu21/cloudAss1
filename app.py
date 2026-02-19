import streamlit as st
import pandas as pd
from cryptography.fernet import Fernet
from fpdf import FPDF
import os
import base64
import json
from datetime import datetime

# ==============================
# CONFIG
# ==============================

st.set_page_config(page_title="Cloud Basics and Infrastructure Quiz", layout="centered")

SECRET_KEY = st.secrets["SECRET_KEY"]
fernet = Fernet(SECRET_KEY.encode())

# ==============================
# DECRYPT FUNCTION
# ==============================

def decrypt_file(enc_file, output_file):
    with open(enc_file, "rb") as f:
        encrypted = f.read()
    decrypted = fernet.decrypt(encrypted)
    with open(output_file, "wb") as f:
        f.write(decrypted)

# ==============================
# LOAD STUDENTS
# ==============================

def load_students():
    decrypt_file("students.xlsx.enc", "students.xlsx")

    try:
        df = pd.read_excel("students.xlsx")
    except:
        df = pd.read_excel("students.xlsx", header=1)

    df.columns = df.columns.str.strip().str.lower()
    os.remove("students.xlsx")
    return df

# ==============================
# LOAD QUESTIONS
# ==============================

def load_questions():
    decrypt_file("questions.xlsx.enc", "questions.xlsx")
    df = pd.read_excel("questions.xlsx")
    df.columns = df.columns.str.strip().str.lower()
    os.remove("questions.xlsx")
    return df

# ==============================
# PROGRESS SAVE
# ==============================

def save_progress(data):
    encrypted = fernet.encrypt(json.dumps(data).encode())
    with open("progress.json.enc", "wb") as f:
        f.write(encrypted)

def load_progress():
    if not os.path.exists("progress.json.enc"):
        return {}
    with open("progress.json.enc", "rb") as f:
        encrypted = f.read()
    decrypted = fernet.decrypt(encrypted)
    return json.loads(decrypted)

# ==============================
# CERTIFICATE GENERATION
# ==============================

def generate_certificate(name, regno, marks):
    pdf = FPDF()
    pdf.add_page()

    # Background Image
    pdf.image("certificate_bg.jpg", x=0, y=0, w=210, h=297)

    pdf.set_font("Arial", "B", 20)
    pdf.ln(80)
    pdf.cell(0, 10, "CERTIFICATE OF COMPLETION", align="C", ln=True)

    pdf.ln(20)
    pdf.set_font("Arial", "", 16)
    pdf.cell(0, 10, f"This is to certify that", align="C", ln=True)

    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, name.upper(), align="C", ln=True)

    pdf.set_font("Arial", "", 14)
    pdf.cell(0, 10, f"Register Number: {regno}", align="C", ln=True)

    pdf.ln(10)
    pdf.cell(0, 10, f"has successfully completed the quiz", align="C", ln=True)
    pdf.cell(0, 10, f"with Marks: {marks}", align="C", ln=True)

    pdf.ln(20)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%d-%m-%Y')}", align="C", ln=True)

    filename = f"certificate_{regno}.pdf"
    pdf.output(filename)
    return filename

# ==============================
# APP START
# ==============================

st.title("☁ Cloud Basics and Infrastructure Quiz")

students = load_students()
questions = load_questions()
progress = load_progress()

# ==============================
# LOGIN SECTION
# ==============================

if "student" not in st.session_state:

    regno_input = st.text_input("Enter Register Number")

    if st.button("Login"):

        reg_column = None
        for col in students.columns:
            if "reg" in col:
                reg_column = col
                break

        if reg_column is None:
            st.error("Register column not found in Excel")
            st.write("Detected Columns:", students.columns.tolist())
            st.stop()

        students[reg_column] = (
            students[reg_column]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
            .str.upper()
        )

        regno_clean = regno_input.strip().upper()
        student = students[students[reg_column] == regno_clean]

        if student.empty:
            st.error("Invalid Register Number")
            st.write("Sample Register Numbers:", students[reg_column].head())
        else:
            st.session_state["student"] = student.iloc[0]
            st.session_state["reg_column"] = reg_column
            st.success("Login Successful")

# ==============================
# QUIZ SECTION
# ==============================

else:

    student = st.session_state["student"]
    reg_column = st.session_state["reg_column"]
    regno = str(student[reg_column])
    name_column = [col for col in students.columns if "name" in col][0]
    name = student[name_column]

    st.success(f"Welcome {name}")

    if regno in progress:
        st.info("You already completed the quiz.")
        marks = progress[regno]["marks"]

        if st.button("Download Certificate"):
            file = generate_certificate(name, regno, marks)
            with open(file, "rb") as f:
                st.download_button("Download PDF", f, file_name=file)

    else:

        q_col = [col for col in questions.columns if "question" in col][0]
        opt_cols = [col for col in questions.columns if "option" in col]
        ans_col = [col for col in questions.columns if "answer" in col][0]

        score = 0
        user_answers = {}

        for i, row in questions.iterrows():
            st.write(f"Q{i+1}: {row[q_col]}")
            selected = st.radio(
                "Choose one:",
                [row[col] for col in opt_cols],
                key=i
            )
            user_answers[i] = selected

        if st.button("Submit Quiz"):

            for i, row in questions.iterrows():
                if user_answers[i] == row[ans_col]:
                    score += 1

            progress[regno] = {
                "name": name,
                "marks": score,
                "date": datetime.now().strftime("%d-%m-%Y")
            }

            save_progress(progress)

            st.success(f"Quiz Completed! Your Score: {score}")

            file = generate_certificate(name, regno, score)

            with open(file, "rb") as f:
                st.download_button("Download Certificate", f, file_name=file)
import streamlit as st
import pandas as pd
from cryptography.fernet import Fernet
from fpdf import FPDF
import os
import base64
import json
from datetime import datetime

# ==============================
# CONFIG
# ==============================

st.set_page_config(page_title="Cloud Basics and Infrastructure Quiz", layout="centered")

SECRET_KEY = st.secrets["SECRET_KEY"]
fernet = Fernet(SECRET_KEY.encode())

# ==============================
# DECRYPT FUNCTION
# ==============================

def decrypt_file(enc_file, output_file):
    with open(enc_file, "rb") as f:
        encrypted = f.read()
    decrypted = fernet.decrypt(encrypted)
    with open(output_file, "wb") as f:
        f.write(decrypted)

# ==============================
# LOAD STUDENTS
# ==============================

def load_students():
    decrypt_file("students.xlsx.enc", "students.xlsx")

    try:
        df = pd.read_excel("students.xlsx")
    except:
        df = pd.read_excel("students.xlsx", header=1)

    df.columns = df.columns.str.strip().str.lower()
    os.remove("students.xlsx")
    return df

# ==============================
# LOAD QUESTIONS
# ==============================

def load_questions():
    decrypt_file("questions.xlsx.enc", "questions.xlsx")
    df = pd.read_excel("questions.xlsx")
    df.columns = df.columns.str.strip().str.lower()
    os.remove("questions.xlsx")
    return df

# ==============================
# PROGRESS SAVE
# ==============================

def save_progress(data):
    encrypted = fernet.encrypt(json.dumps(data).encode())
    with open("progress.json.enc", "wb") as f:
        f.write(encrypted)

def load_progress():
    if not os.path.exists("progress.json.enc"):
        return {}
    with open("progress.json.enc", "rb") as f:
        encrypted = f.read()
    decrypted = fernet.decrypt(encrypted)
    return json.loads(decrypted)

# ==============================
# CERTIFICATE GENERATION
# ==============================

def generate_certificate(name, regno, marks):
    pdf = FPDF()
    pdf.add_page()

    # Background Image
    pdf.image("certificate_bg.jpg", x=0, y=0, w=210, h=297)

    pdf.set_font("Arial", "B", 20)
    pdf.ln(80)
    pdf.cell(0, 10, "CERTIFICATE OF COMPLETION", align="C", ln=True)

    pdf.ln(20)
    pdf.set_font("Arial", "", 16)
    pdf.cell(0, 10, f"This is to certify that", align="C", ln=True)

    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, name.upper(), align="C", ln=True)

    pdf.set_font("Arial", "", 14)
    pdf.cell(0, 10, f"Register Number: {regno}", align="C", ln=True)

    pdf.ln(10)
    pdf.cell(0, 10, f"has successfully completed the quiz", align="C", ln=True)
    pdf.cell(0, 10, f"with Marks: {marks}", align="C", ln=True)

    pdf.ln(20)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%d-%m-%Y')}", align="C", ln=True)

    filename = f"certificate_{regno}.pdf"
    pdf.output(filename)
    return filename

# ==============================
# APP START
# ==============================

st.title("☁ Cloud Basics and Infrastructure Quiz")

students = load_students()
questions = load_questions()
progress = load_progress()

# ==============================
# LOGIN SECTION
# ==============================

if "student" not in st.session_state:

    regno_input = st.text_input("Enter Register Number")

    if st.button("Login"):

        reg_column = None
        for col in students.columns:
            if "reg" in col:
                reg_column = col
                break

        if reg_column is None:
            st.error("Register column not found in Excel")
            st.write("Detected Columns:", students.columns.tolist())
            st.stop()

        students[reg_column] = (
            students[reg_column]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
            .str.upper()
        )

        regno_clean = regno_input.strip().upper()
        student = students[students[reg_column] == regno_clean]

        if student.empty:
            st.error("Invalid Register Number")
            st.write("Sample Register Numbers:", students[reg_column].head())
        else:
            st.session_state["student"] = student.iloc[0]
            st.session_state["reg_column"] = reg_column
            st.success("Login Successful")

# ==============================
# QUIZ SECTION
# ==============================

else:

    student = st.session_state["student"]
    reg_column = st.session_state["reg_column"]
    regno = str(student[reg_column])
    name_column = [col for col in students.columns if "name" in col][0]
    name = student[name_column]

    st.success(f"Welcome {name}")

    if regno in progress:
        st.info("You already completed the quiz.")
        marks = progress[regno]["marks"]

        if st.button("Download Certificate"):
            file = generate_certificate(name, regno, marks)
            with open(file, "rb") as f:
                st.download_button("Download PDF", f, file_name=file)

    else:

        q_col = [col for col in questions.columns if "question" in col][0]
        opt_cols = [col for col in questions.columns if "option" in col]
        ans_col = [col for col in questions.columns if "answer" in col][0]

        score = 0
        user_answers = {}

        for i, row in questions.iterrows():
            st.write(f"Q{i+1}: {row[q_col]}")
            selected = st.radio(
                "Choose one:",
                [row[col] for col in opt_cols],
                key=i
            )
            user_answers[i] = selected

        if st.button("Submit Quiz"):

            for i, row in questions.iterrows():
                if user_answers[i] == row[ans_col]:
                    score += 1

            progress[regno] = {
                "name": name,
                "marks": score,
                "date": datetime.now().strftime("%d-%m-%Y")
            }

            save_progress(progress)

            st.success(f"Quiz Completed! Your Score: {score}")

            file = generate_certificate(name, regno, score)

            with open(file, "rb") as f:
                st.download_button("Download Certificate", f, file_name=file)
