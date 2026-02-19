import streamlit as st
import pandas as pd
import pyAesCrypt
import json
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from datetime import datetime

# ---------------- CONFIG ----------------
bufferSize = 64 * 1024
PASSWORD = st.secrets["ENC_KEY"]

st.set_page_config(page_title="Online Quiz", page_icon="🎓")

# ---------------- DECRYPT FUNCTION ----------------
def decrypt_file(enc_file, output_file):
    if not os.path.exists(enc_file):
        st.error(f"{enc_file} not found in repository.")
        st.stop()
    pyAesCrypt.decryptFile(enc_file, output_file, PASSWORD, bufferSize)

# ---------------- LOAD STUDENTS ----------------
def load_students():
    decrypt_file("students.xlsx.enc", "students.xlsx")

    # Read 2nd row as header
    df = pd.read_excel("students.xlsx", header=1)
    os.remove("students.xlsx")

    df.columns = df.columns.astype(str).str.strip()

    df = df.rename(columns={
        "reg_no": "RegNo",
        "Student Name": "Name",
        "Dept": "Dept",
        "Year": "Year",
        "Section": "Section"
    })

    df = df[["RegNo", "Name", "Dept", "Year", "Section"]]
    df["RegNo"] = df["RegNo"].astype(str).str.strip()

    return df

# ---------------- LOAD QUESTIONS ----------------
def load_questions():
    decrypt_file("questions.xlsx.enc", "questions.xlsx")

    # Read 2nd row as header
    df = pd.read_excel("questions.xlsx", header=1)
    os.remove("questions.xlsx")

    df.columns = df.columns.astype(str).str.strip()

    df = df.rename(columns={
        "Question": "Question",
        "Option1": "A",
        "Option2": "B",
        "Option3": "C",
        "Option4": "D",
        "Right Answer": "Correct"
    })

    # Convert Option1 → A etc.
    def convert_answer(ans):
        if ans == "Option1":
            return "A"
        elif ans == "Option2":
            return "B"
        elif ans == "Option3":
            return "C"
        elif ans == "Option4":
            return "D"
        return ans

    df["Correct"] = df["Correct"].apply(convert_answer)

    return df

# ---------------- LOAD PROGRESS ----------------
def load_progress():
    decrypt_file("progress.enc", "progress.json")
    with open("progress.json", "r") as f:
        data = json.load(f)
    os.remove("progress.json")
    return data

def save_progress(data):
    with open("progress.json", "w") as f:
        json.dump(data, f)

    pyAesCrypt.encryptFile("progress.json", "progress.enc", PASSWORD, bufferSize)
    os.remove("progress.json")

# ---------------- CERTIFICATE ----------------
def generate_certificate(student, score, total):
    file_name = f"{student['RegNo']}_certificate.pdf"
    doc = SimpleDocTemplate(file_name)
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>Certificate of Achievement</b>", styles["Title"]))
    elements.append(Spacer(1, 0.5 * inch))

    text = f"""
    This is to certify that <b>{student['Name']}</b><br/><br/>
    Registration Number: {student['RegNo']}<br/>
    Department: {student['Dept']}<br/>
    Year: {student['Year']} | Section: {student['Section']}<br/><br/>
    has successfully completed the Online Quiz<br/><br/>
    Score Obtained: <b>{score} / {total}</b><br/><br/>
    Date: {datetime.today().strftime('%d-%m-%Y')}
    """

    elements.append(Paragraph(text, styles["Normal"]))
    doc.build(elements)

    return file_name

# ---------------- MAIN APP ----------------
st.title("🎓 Online Quiz & Certificate System")

students = load_students()
questions = load_questions()
progress = load_progress()

regno = st.text_input("Enter Registration Number")

if regno:

    regno = regno.strip()

    if regno not in students["RegNo"].values:
        st.error("Invalid Registration Number")
    else:
        student = students[students["RegNo"] == regno].iloc[0].to_dict()

        # Already completed
        if regno in progress and progress[regno]["completed"]:

            st.warning("⚠ You have already completed the quiz.")

            cert_file = generate_certificate(
                student,
                progress[regno]["score"],
                progress[regno]["total"]
            )

            with open(cert_file, "rb") as f:
                st.download_button(
                    "📥 Download Certificate",
                    f,
                    file_name=cert_file
                )

        else:
            st.success(f"Welcome {student['Name']}")

            answers = {}

            for i, row in questions.iterrows():
                answers[i] = st.radio(
                    row["Question"],
                    [row["A"], row["B"], row["C"], row["D"]],
                    key=i
                )

            if st.button("Submit Quiz"):

                score = 0

                for i, row in questions.iterrows():
                    correct_option = row[row["Correct"]]
                    if answers[i] == correct_option:
                        score += 1

                progress[regno] = {
                    "score": score,
                    "total": len(questions),
                    "completed": True
                }

                save_progress(progress)

                st.success(f"✅ Your Score: {score}/{len(questions)}")

                cert_file = generate_certificate(student, score, len(questions))

                with open(cert_file, "rb") as f:
                    st.download_button(
                        "📥 Download Certificate",
                        f,
                        file_name=cert_file
                    )
