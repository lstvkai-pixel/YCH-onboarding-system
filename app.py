import sqlite3
import streamlit as st
import urllib.parse
import re
import pandas as pd
import io
import os
from datetime import datetime, timedelta
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# ==========================================
# DATABASE ENTERPRISE BACKEND LOGIC
# ==========================================
def get_db_connection():
    return sqlite3.connect("onboarding.db")

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Updated user_accounts with password reset flag
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL DEFAULT 'YCH1234',
            role_type TEXT NOT NULL DEFAULT 'Employee',
            force_password_change INTEGER DEFAULT 1
        )
    ''')
    
    # ... (Keep existing tables: new_hires, training_logs, tasks, signed_documents, lms_materials, certifications, feedback_tickets, announcements, managers)
    # Ensure tables are created if missing
    cursor.execute('CREATE TABLE IF NOT EXISTS new_hires (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT, name TEXT, role TEXT, department TEXT, manager TEXT, start_date TEXT, gender TEXT, status TEXT DEFAULT "Active", photo_path TEXT, phase3_approved INTEGER DEFAULT 0, phase4_approved INTEGER DEFAULT 0, phase5_approved INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS training_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, log_date TEXT, classroom_hours INTEGER, ojt_hours INTEGER, safety_hours INTEGER, technical_hours INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, task_name TEXT, phase TEXT, assigned_to TEXT, department TEXT, is_completed INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS signed_documents (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, doc_name TEXT, file_path TEXT, date_uploaded TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS lms_materials (id INTEGER PRIMARY KEY AUTOINCREMENT, phase TEXT, title TEXT, doc_type TEXT, file_path TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS certifications (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, cert_name TEXT, issue_date TEXT, expiry_date TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS feedback_tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, category TEXT, content TEXT, ticket_status TEXT, date_logged TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, content TEXT, date_posted TEXT, file_path TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS managers (id INTEGER PRIMARY KEY AUTOINCREMENT, manager_name TEXT UNIQUE)')

    cursor.execute("INSERT OR IGNORE INTO user_accounts (employee_id, password, role_type, force_password_change) VALUES ('HR0001', 'YCHADMIN', 'Employer', 0)")
    
    conn.commit()
    conn.close()

init_database()

# ==========================================
# AUTHENTICATION & PASSWORD FLOW
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.update({"authenticated": False, "username": None, "user_role": None, "change_pwd": False})

if not st.session_state["authenticated"]:
    # Login UI
    st.title("🔑 YCH Group Access Portal")
    user = st.text_input("Employee ID:").strip().upper()
    pwd = st.text_input("Password:", type="password")
    if st.button("Sign In"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password, role_type, force_password_change FROM user_accounts WHERE employee_id = ?", (user,))
        data = cursor.fetchone()
        conn.close()
        if data and data[0] == pwd:
            st.session_state.update({"authenticated": True, "username": user, "user_role": data[1]})
            if data[2] == 1: st.session_state["change_pwd"] = True
            st.rerun()
        else: st.error("Invalid credentials.")
    st.stop()

if st.session_state["change_pwd"]:
    st.warning("⚠️ First-time login: Please change your password.")
    new_pwd = st.text_input("New Password:", type="password")
    if st.button("Update Password"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE user_accounts SET password = ?, force_password_change = 0 WHERE employee_id = ?", (new_pwd, st.session_state["username"]))
        conn.commit()
        conn.close()
        st.session_state["change_pwd"] = False
        st.rerun()
    st.stop()

# ==========================================
# DASHBOARD (Add the WhatsApp Trigger inside "Add New Employee")
# ==========================================
# Inside the "Add New Employee" block, add this:

# ... after inserting into user_accounts ...
# whatsapp_text = f"Hi! Welcome to YCH. Your login: {input_emp_id}, Default Password: YCH1234. Please change it upon login."
# st.markdown(f'<a href="https://wa.me/{clean_mob}?text={urllib.parse.quote(whatsapp_text)}" target="_blank">Send Credentials via WhatsApp</a>', unsafe_allow_html=True)
