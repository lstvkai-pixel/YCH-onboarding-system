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
    cursor.execute('''CREATE TABLE IF NOT EXISTS new_hires (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT, mobile_number TEXT, name TEXT, role TEXT, department TEXT, manager TEXT, start_date TEXT, gender TEXT, status TEXT DEFAULT "Active", photo_path TEXT, phase3_approved INTEGER DEFAULT 0, phase4_approved INTEGER DEFAULT 0, phase5_approved INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT UNIQUE, password TEXT DEFAULT 'YCH1234', role_type TEXT DEFAULT 'Employee', force_password_change INTEGER DEFAULT 1)''')
    cursor.execute("INSERT OR IGNORE INTO user_accounts (employee_id, password, role_type, force_password_change) VALUES ('HR0001', 'YCHADMIN', 'Employer', 0)")
    cursor.execute('''CREATE TABLE IF NOT EXISTS training_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, log_date TEXT, classroom_hours INTEGER, ojt_hours INTEGER, safety_hours INTEGER, technical_hours INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, task_name TEXT, phase TEXT, assigned_to TEXT, department TEXT, is_completed INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS signed_documents (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, doc_name TEXT, file_path TEXT, date_uploaded TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS lms_materials (id INTEGER PRIMARY KEY AUTOINCREMENT, phase TEXT, title TEXT, doc_type TEXT, file_path TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS certifications (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, cert_name TEXT, issue_date TEXT, expiry_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS feedback_tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, category TEXT, content TEXT, ticket_status TEXT DEFAULT 'Open', date_logged TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, content TEXT, date_posted TEXT, file_path TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS managers (id INTEGER PRIMARY KEY AUTOINCREMENT, manager_name TEXT UNIQUE)''')
    conn.commit()
    conn.close()

init_database()

# ==========================================
# AUTHENTICATION ROUTER
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.update({"authenticated": False, "username": None, "user_role": None, "change_pwd": False})

if not st.session_state["authenticated"]:
    st.title("🔑 YCH Group Access Portal")
    user = st.text_input("Employee ID / Admin ID:").strip().upper()
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
    st.warning("⚠️ First-time login: Please update your password.")
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

# Logout
if st.sidebar.button("🚪 Logout"):
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# ==========================================
# MAIN INTERFACE
# ==========================================
# Admin vs Employee logic flows here (using your existing dashboard code)
# Remember to filter 'new_hires' query with "WHERE employee_id = '{st.session_state['username']}'" for Employees
# and keep the full Admin panel available only if st.session_state["user_role"] == "Employer"
