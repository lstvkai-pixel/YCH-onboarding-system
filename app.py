import sqlite3
import streamlit as st
import urllib.parse
import re
import pandas as pd
import io
import os
import base64
from datetime import datetime, timedelta
import plotly.express as px

# Set page config
st.set_page_config(page_title="YCH EX Platform", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# DATABASE ENTERPRISE BACKEND LOGIC
# ==========================================
def get_db_connection():
    return sqlite3.connect("onboarding.db", check_same_thread=False, timeout=30)

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS new_hires (
        id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT, mobile_number TEXT, 
        name TEXT, role TEXT, department TEXT, manager TEXT, start_date TEXT, 
        gender TEXT, status TEXT DEFAULT "Active", photo_path TEXT, 
        phase3_approved INTEGER DEFAULT 0, phase4_approved INTEGER DEFAULT 0, phase5_approved INTEGER DEFAULT 0)''')
    
    # Safely upgrade existing database with new birthday column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE new_hires ADD COLUMN birthday TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists, safe to ignore

    cursor.execute('''CREATE TABLE IF NOT EXISTS user_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id TEXT UNIQUE, 
        password TEXT DEFAULT 'YCH1234', role_type TEXT DEFAULT 'Employee', 
        force_password_change INTEGER DEFAULT 1)''')
    cursor.execute("INSERT OR IGNORE INTO user_accounts (employee_id, password, role_type, force_password_change) VALUES ('HR0001', 'YCHADMIN', 'Employer', 0)")
    cursor.execute('''CREATE TABLE IF NOT EXISTS training_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, log_date TEXT, classroom_hours INTEGER, ojt_hours INTEGER, safety_hours INTEGER, technical_hours INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, task_name TEXT, phase TEXT, assigned_to TEXT, department TEXT, is_completed INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS signed_documents (id INTEGER PRIMARY KEY AUTOINCREMENT, hire_id INTEGER, doc_name TEXT, file_path TEXT, date_uploaded TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS lms_materials (id INTEGER PRIMARY KEY AUTOINCREMENT, phase TEXT, title TEXT, doc_type TEXT, file_path TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, content TEXT, date_posted TEXT, file_path TEXT, expiry_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS managers (id INTEGER PRIMARY KEY AUTOINCREMENT, manager_name TEXT UNIQUE)''')
    conn.commit()
    conn.close()

init_database()

# ==========================================
# CORPORATE THEME & CSS (MOCKUP STYLING)
# ==========================================
st.markdown("""
    <style>
        /* Base App Styling */
        .stApp { background-color: #F4F7FB; }
        
        /* Remove top padding for custom header */
        .block-container { padding-top: 1rem !important; }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] { background-color: #002060; }
        [data-testid="stSidebar"] * { color: #FFFFFF !important; }
        
        [data-testid="stSidebar"] button {
            background-color: transparent !important;
            color: #FFFFFF !important;
            border: 1px solid #FFFFFF !important;
            border-radius: 4px;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] button:hover {
            background-color: rgba(255,255,255,0.1) !important;
        }
        
        /* Custom KPI Card Styling */
        .kpi-container {
            display: flex;
            align-items: center;
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
            border: 1px solid #E2E8F0;
            height: 110px;
        }
        .kpi-icon-box {
            background-color: #002060;
            color: white;
            border-radius: 50%;
            width: 55px;
            height: 55px;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 24px;
            margin-right: 15px;
            flex-shrink: 0;
        }
        .kpi-text-box {
            display: flex;
            flex-direction: column;
        }
        .kpi-label {
            font-size: 14px;
            color: #64748B;
            font-weight: 600;
            margin: 0;
        }
        .kpi-value {
            font-size: 32px;
            color: #002060;
            font-weight: 800;
            margin: 0;
            line-height: 1.2;
        }
        
        /* Action Buttons */
        .ych-action-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            width: 100%;
            height: 42px;
            border: none;
            border-radius: 6px;
            color: white;
            font-weight: bold;
            font-size: 13px;
            cursor: pointer;
            text-decoration: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        .ych-action-btn:hover { opacity: 0.9; }
        
        /* Sidebar Logo White Box */
        [data-testid="stSidebar"] img {
            background-color: #FFFFFF;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# Custom Top Header Function
def render_top_header():
    user_initial = st.session_state['username'][0].upper() if st.session_state['username'] else "U"
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; background-color: #FFFFFF; padding: 15px 25px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-bottom: 3px solid #EAA221; margin-bottom: 25px;">
            <div style="display: flex; align-items: center; gap: 15px;">
                <div>
                    <h2 style="color: #002060; margin: 0; font-weight: 900; letter-spacing: 1px; font-size: 24px;">YCH EMPLOYEE EXPERIENCE</h2>
                    <span style="color: #EAA221; font-weight: 600; font-size: 12px; letter-spacing: 2px;">WHERE PEOPLE CONNECT</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 15px;">
                <div style="text-align: right;">
                    <div style="color: #1E293B; font-weight: bold; font-size: 14px;">{st.session_state['username']}</div>
                    <div style="color: #64748B; font-size: 12px;">{st.session_state['user_role']}</div>
                </div>
                <div style="background-color: #002060; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 18px;">
                    {user_initial}
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# CORE CONSTANTS & PARAMETERS
# ==========================================
YCH_DEPARTMENTS = [
    "HR Department", "QAEHS Department", "Procurement Department",
    "Freight & Transport Department", "Finance Department", "Ops Abott_Inplant",
    "Ops Symrise Flavours SG", "Ops Symrise", "Ops Starbucks", "Ops HAP",
    "Ops LKK", "Ops 3M_Tech", "Ops 3M_Odessy", "Ops Philip_PH", "Ops Philip_HS"
]

AVAILABLE_TEAMS = ["HR Team", "Security Team", "QA&EHS Team", "Ops Team"]

PHASE_GROUPS = [
    "Phase 1: Pre-boarding Checklist",
    "Phase 2: Day 1 Checklist",
    "Phase 3: Technical Training Checklist",
    "Phase 4: Performance Assessment Checklist",
    "Phase 5: Employee Engagement & Follow-up Checklist"
]

# ==========================================
# INFRASTRUCTURE HELPER LOGIC PIPELINES
# ==========================================
def calculate_metrics_pipeline(hire_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(is_completed) FROM tasks WHERE hire_id = ?", (hire_id,))
    t_tot, t_comp = cursor.fetchone()
    t_comp = t_comp if t_comp else 0
    overall = int((t_comp / t_tot) * 100) if t_tot > 0 else 0
    
    phase_data = {}
    for phase_str in PHASE_GROUPS:
        p_short = phase_str.split(":")[0]
        cursor.execute("SELECT COUNT(*), SUM(is_completed) FROM tasks WHERE hire_id = ? AND phase = ?", (hire_id, phase_str))
        p_tot, p_comp = cursor.fetchone()
        p_comp = p_comp if p_comp else 0
        phase_data[p_short] = int((p_comp / p_tot) * 100) if p_tot > 0 else 0
        
    conn.close()
    return overall, phase_data

def evaluate_achievements(hire_id, overall, phase_data):
    badges = []
    if phase_data.get("Phase 1") == 100: badges.append("🏆 Fast Starter")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE hire_id = ? AND assigned_to = 'QA&EHS Team' AND is_completed = 0", (hire_id,))
    pending_safety = cursor.fetchone()[0]
    if pending_safety == 0: badges.append("🏅 Safety Champion")
    conn.close()
    if phase_data.get("Phase 3") == 100: badges.append("🚀 Technical Expert")
    if phase_data.get("Phase 4") == 100: badges.append("⭐ Independent Performer")
    if overall == 100: badges.append("🎓 Onboarding Graduate")
    return badges

def assign_status_health(overall):
    if overall >= 80: return "🟢 On Track"
    if overall >= 50: return "🟡 Delayed"
    return "🔴 Critical"

# ==========================================
# STATE MACHINE INITIALIZATION
# ==========================================
for state_key, default_value in [
    ("authenticated", False),
    ("username", None),
    ("user_role", None),
    ("change_pwd", False),
    ("confirm_delete_stage", False), 
    ("target_purge_id", None), 
    ("ann_posted_success", False),
    ("profile_updated", False)  # Added this specifically for the Save Button fix!
]:
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value

if not st.session_state.get("authenticated", False):
    st.markdown("<h1 style='color: #003366; text-align: center; font-family: sans-serif; font-weight: 900; margin-top:50px;'>🏢 YCH GROUP EXPERIENCE LABS</h1>", unsafe_allow_html=True)
    st.markdown("<h5 style='color: #EAA221; text-align: center; font-family: sans-serif; font-weight: 600;'>Workforce Onboarding Portal</h5>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.subheader("🔑 Identity Secure Access Sign-In")
        login_user = st.text_input("User Employee ID / Username ID:").strip().upper()
        login_pass = st.text_input("Account Access Password:", type="password")
        
        if st.button("Authorize Portal Entry", use_container_width=True, type="primary"):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT password, role_type, force_password_change FROM user_accounts WHERE employee_id = ?", (login_user,))
            data = cursor.fetchone()
            conn.close()
            
            if data and data[0] == login_pass:
                st.session_state["authenticated"] = True
                st.session_state["username"] = login_user
                st.session_state["user_role"] = data[1]
                st.session_state["change_pwd"] = True if data[2] == 1 else False
                st.success("Access tokens granted. Directing to assigned workspace nodes...")
                st.rerun()
            else:
                st.error("Authentication Intercepted: Invalid username or password provided.")
    st.stop()

if st.session_state.get("change_pwd", False):
    st.warning("⚠️ First-time login: Please update your default password.")
    new_pwd = st.text_input("New Password:", type="password")
    if st.button("Update Password", use_container_width=True, type="primary"):
        if new_pwd.strip() != "":
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE user_accounts SET password = ?, force_password_change = 0 WHERE employee_id = ?", (new_pwd, st.session_state["username"]))
            conn.commit()
            conn.close()
            st.session_state["change_pwd"] = False
            st.success("Password secured! Redirecting...")
            st.rerun()
        else:
            st.error("Password cannot be blank.")
    st.stop()

# Render custom top bar for logged-in users
render_top_header()

# Render Logo right above the terminate button in the Sidebar
st.sidebar.markdown("<br><br><br>", unsafe_allow_html=True)
st.sidebar.markdown('''
    <style>
        [data-testid="stSidebar"] img {
            background-color: #FFFFFF;
            padding: 15px;
            border-radius: 8px;
        }
    </style>
''', unsafe_allow_html=True)
if os.path.exists("YCH-EX.jpeg"):
    st.sidebar.image("YCH-EX.jpeg", use_container_width=True)
st.sidebar.markdown("<br>", unsafe_allow_html=True)

if st.sidebar.button("🚪 Terminate Portal Session", use_container_width=True):
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# ==========================================
# HUB INTERFACE ROADMAP 1: EMPLOYEE PORTAL RUNTIME
# ==========================================
if st.session_state["user_role"] == "Employee":
    st.sidebar.markdown(
        f"👤 **User Code:** <span style='background-color:rgba(255,255,255,0.2); padding: 3px 8px; border-radius: 4px; color: #FFFFFF;'>{st.session_state['username']}</span>", 
        unsafe_allow_html=True
    )
    
    st.sidebar.markdown("🔰 **Access Level:** Employee Dashboard")
    st.sidebar.markdown("---")
    
    emp_menu = st.sidebar.radio("WORK ENVIRONMENT", ["📋 My Onboarding Journey Map", "📚 Library Training center"])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, role, department, manager, start_date, mobile_number, photo_path, phase3_approved, phase4_approved, phase5_approved FROM new_hires WHERE UPPER(employee_id) = ?", (st.session_state["username"],))
    emp_node = cursor.fetchone()
    conn.close()
    
    if not emp_node:
        st.warning("⚠️ Profile Configuration Exception: Your candidate account profile has not been initialized in the new hires table layout yet. Contact your HR manager PIC.")
    else:
        h_id, name, role, dept, manager, start_date, mobile, photo, p3_a, p4_a, p5_a = emp_node
        ovr_pct, p_breakdown = calculate_metrics_pipeline(h_id)
        health_state = assign_status_health(ovr_pct)
        earned_achievements = evaluate_achievements(h_id, ovr_pct, p_breakdown)
        
        if emp_menu == "📋 My Onboarding Journey Map":
            st.markdown("### 📋 My Onboarding Experience Journey Roadmap")
            
            with st.container(border=True):
                dc1, dc2 = st.columns([1, 4])
                with dc1:
                    if photo and os.path.exists(photo): st.image(photo, width=120)
                    else: st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=120)
                with dc2:
                    st.subheader(f"Welcome, {name}!")
                    st.markdown(f"🆔 **Employee ID:** `{st.session_state['username']}` | 💼 **Position Role:** `{role}`")
                    st.markdown(f"🏢 **Assigned Department:** `{dept}` | 👤 **Reporting Manager PIC:** `{manager}`")
                    st.markdown(f"📈 **Onboarding Status Health:** {health_state}")
                    
                    if earned_achievements:
                        st.markdown(" ".join([f"<span style='background-color:#E2E8F0; padding:3px 8px; border-radius:12px; font-size:12px; margin-right:5px; font-weight:bold; color:#003366;'>{b}</span>" for b in earned_achievements]), unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### Onboarding Journey Track Progress Map")
            
            m_cols = st.columns(5)
            for step_idx, phase_spec in enumerate(PHASE_GROUPS):
                p_code = phase_spec.split(":")[0]
                p_val = p_breakdown[p_code]
                
                with m_cols[step_idx]:
                    bg_lbl = "🔵" if p_val == 100 else ("🟠" if p_val > 0 else "⚪")
                    st.markdown(f"<div style='text-align:center; font-size:12px; background:#FFFFFF; padding:8px; border-radius:6px; border:1px solid #E2E8F0; box-shadow:0 1px 3px rgba(0,0,0,0.05);'>{bg_lbl} <b>{p_code}</b><br><span style='font-size:16px; font-weight:bold; color:#002060;'>{p_val}%</span></div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 📋 Detailed Individual Milestones Task Checklist Logs")
            for current_phase in PHASE_GROUPS:
                with st.expander(f"📌 {current_phase} (Progress Fraction: {p_breakdown[current_phase.split(':')[0]]}%)"):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT task_name, assigned_to, is_completed FROM tasks WHERE hire_id = ? AND phase = ?", (h_id, current_phase))
                    ptasks = cursor.fetchall()
                    conn.close()
                    
                    if not ptasks: st.caption("_No roadmap parameters verified onto this phase container block currently._")
                    for t_name, team, comp in ptasks:
                        icon_s = "✅ Complete" if comp else "⏳ Pending Processing"
                        st.markdown(f"• **{t_name}** — `[{icon_s}]` | Ownership Action Team Role: `{team}`")

        elif emp_menu == "📚 Library Training center":
            st.markdown("### 📚 Distributed Training Document Library")
            
            sel_phase = st.selectbox("Select Onboarding Phase roadmap target context:", PHASE_GROUPS)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT title, doc_type, file_path FROM lms_materials WHERE phase = ?", (sel_phase,))
            items = cursor.fetchall()
            conn.close()
            
            if not items:
                st.info("No training materials or manuals published by administrators onto this phase context layer yet.")
            else:
                for title, d_type, f_path in items:
                    st.markdown(f"📄 **{title}** `[{d_type}]` — _Read and understand guidelines carefully._")
                    if f_path and os.path.exists(f_path):
                        file_ext = f_path.split('.')[-1].lower()
                        
                        with st.expander(f"👁️ Open and Read: {title}"):
                            if file_ext in ['png', 'jpg', 'jpeg']:
                                st.image(f_path, use_container_width=True)
                            elif file_ext == 'pdf':
                                with open(f_path, "rb") as f:
                                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                                
                                # Use native markdown iframe to bypass Edge/Chrome Sandboxing blocks
                                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#toolbar=0&navpanes=0" width="100%" height="800px" style="border: none;"></iframe>'
                                st.markdown(pdf_display, unsafe_allow_html=True)
                            else:
                                st.info("Preview not available for this file type.")
                    st.markdown("---")
    st.stop()

# ==========================================
# HUB INTERFACE ROADMAP 2: EMPLOYER PORTAL RUNTIME
# ==========================================
elif st.session_state["user_role"] == "Employer":
    menu = st.sidebar.radio(
        "NAVIGATION HUB", 
        [
            "🏠 Corporate Experience Landing", 
            "➕ Add New Employee", 
            "📋 Task Checklist View", 
            "📚 Rules and Guidelines", 
            "📤 Export Reports", 
            "🚨 System Administration"
        ]
    )

    # --- WORKSPACE 1: HR CORPORATE LANDING PAGE ---
    if menu == "🏠 Corporate Experience Landing":
        st.info("🤝 **Our Welcome Charter:** Welcome to YCH Group. We are committed to developing world-class logistics professionals through structured onboarding, technical excellence, safety leadership, and continuous learning.")
        
        # High Level Enterprise Metric Scorecards
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM new_hires WHERE status = 'Active'")
        act_c = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM new_hires WHERE status = 'Archived'")
        grad_c = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM new_hires WHERE status = 'Active'")
        act_ids = cursor.fetchall()
        tot_rate = 0
        for rid in act_ids:
            ovr, _ = calculate_metrics_pipeline(rid[0])
            tot_rate += ovr
        avg_rate = int(tot_rate / act_c) if act_c > 0 else 0
        conn.close()
        
        # Custom HTML KPI Cards based on Mockup
        k1, k2, k3, k4 = st.columns(4)
        with k1: 
            st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-icon-box">👥</div>
                <div class="kpi-text-box">
                    <p class="kpi-label">Active Tracks</p>
                    <p class="kpi-value">{act_c}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with k2: 
            st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-icon-box">🎓</div>
                <div class="kpi-text-box">
                    <p class="kpi-label">Completed Onboarding</p>
                    <p class="kpi-value">{grad_c}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with k3: 
            st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-icon-box">📈</div>
                <div class="kpi-text-box">
                    <p class="kpi-label">Avg Completion</p>
                    <p class="kpi-value">{avg_rate}%</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with k4: 
            st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-icon-box">👤+</div>
                <div class="kpi-text-box">
                    <p class="kpi-label">New Hires (Month)</p>
                    <p class="kpi-value">{act_c}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        tab_dash, tab_news = st.tabs(["📊 Active Journeys Grid", "📢 Corporate News Feed"])
        
        with tab_dash:
            # === NEW SEARCH FEATURE ===
            st.markdown("#### 🔍 Employee Directory Search")
            search_query = st.text_input("Search active employees by ID, Name, Department, or Role:", placeholder="e.g. SG0001, John, HR, Admin...").strip().upper()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Filter dataset based on the search input
            if search_query:
                cursor.execute("""
                    SELECT id, employee_id, name, role, department, manager, start_date, mobile_number, photo_path, phase3_approved, phase4_approved, phase5_approved 
                    FROM new_hires 
                    WHERE status = 'Active' AND (
                        UPPER(name) LIKE ? OR 
                        UPPER(employee_id) LIKE ? OR 
                        UPPER(role) LIKE ? OR 
                        UPPER(department) LIKE ?
                    )
                """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
            else:
                cursor.execute("SELECT id, employee_id, name, role, department, manager, start_date, mobile_number, photo_path, phase3_approved, phase4_approved, phase5_approved FROM new_hires WHERE status = 'Active'")
            
            active_dataset = cursor.fetchall()
            conn.close()
            
            if not active_dataset:
                if search_query:
                    st.warning(f"No active employees found matching '{search_query}'.")
                else:
                    st.info("No active onboarding profiles running inside the logistics roadmap track pipelines.")
            else:
                if search_query:
                    st.success(f"Found {len(active_dataset)} matching profile(s).")
                    
                for node in active_dataset:
                    h_id, emp_id, name, role, dept, manager, start_date, mobile, photo, p3_a, p4_a, p5_a = node
                    ovr_pct, p_breakdown = calculate_metrics_pipeline(h_id)
                    health_state = assign_status_health(ovr_pct)
                    earned_achievements = evaluate_achievements(h_id, ovr_pct, p_breakdown)
                    
                    with st.container(border=True):
                        dc1, dc2, dc3 = st.columns([1, 3, 2])
                        with dc1:
                            if photo and os.path.exists(photo): st.image(photo, width=120)
                            else: st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=120)
                        with dc2:
                            st.subheader(f"{name} ({emp_id})")
                            st.markdown(f"💼 **{role}** | 🏬 {dept} | 👤 PIC: *{manager}*")
                            st.markdown(f"📱 Contact: `{mobile}` | 📅 Started: *{start_date}*")
                            st.markdown(f"📈 Status: **{health_state}**")
                            
                            if earned_achievements:
                                st.markdown(" ".join([f"<span style='background-color:#E2E8F0; padding:3px 8px; border-radius:12px; font-size:12px; margin-right:5px; font-weight:bold; color:#003366;'>{b}</span>" for b in earned_achievements]), unsafe_allow_html=True)
                        with dc3:
                            st.markdown(f"<div style='text-align:center;'><p style='margin:0; font-size:14px; color:#64748B;'>Overall Completion</p><h2 style='margin:0; color:#002060;'>{ovr_pct}%</h2></div>", unsafe_allow_html=True)
                            st.progress(ovr_pct / 100)
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                            raw_channel_msg = f"🚨 *[YCH_HR Alert] New Employee Onboarding Scheduled*\n\n*Employee Details*\n• *ID:* {emp_id}\n• *Name:* {name}\n• *Dept:* {dept}\n• *Role:* {role}\n• *Manager:* {manager}\n• *Start:* {start_date}"
                            encoded_channel = urllib.parse.quote(raw_channel_msg)
                            channel_url = f"https://api.whatsapp.com/send?phone=&text={encoded_channel}"
                            
                            raw_progress_msg = f"📊 *YCH Progress Update*\n\n• *ID:* {emp_id}\n• *Name:* {name}\n\n📈 *Overall Completion:* {ovr_pct}%"
                            clean_phone = re.sub(r'\D', '', mobile)
                            encoded_progress = urllib.parse.quote(raw_progress_msg)
                            employee_sms_url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_progress}"

                            st.markdown(f"""
                                <div style='display: flex; gap: 10px; width: 100%;'>
                                    <a href='{channel_url}' target='_blank' style='flex: 1; text-decoration: none;'>
                                        <button class='ych-action-btn' style='background-color: #003366;'>📢 Broadcast</button>
                                    </a>
                                    <a href='{employee_sms_url}' target='_blank' style='flex: 1; text-decoration: none;'>
                                        <button class='ych-action-btn' style='background-color: #25D366;'>📲 Progress</button>
                                    </a>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            if ovr_pct == 100 and p3_a and p4_a and p5_a:
                                st.markdown("<br>", unsafe_allow_html=True)
                                st.success("🎓 Onboarding Fully Completed!")

                        st.markdown("<br>", unsafe_allow_html=True)
                        m_cols = st.columns(5)
                        for step_idx, phase_spec in enumerate(PHASE_GROUPS):
                            p_code = phase_spec.split(":")[0]
                            p_val = p_breakdown[p_code]
                            with m_cols[step_idx]:
                                bg_color = "#3B82F6" if p_val == 100 else ("#F59E0B" if p_val > 0 else "#E2E8F0")
                                text_color = "white" if p_val > 0 else "#64748B"
                                st.markdown(f"<div style='text-align:center; font-size:12px; background:{bg_color}; color:{text_color}; padding:5px; border-radius:4px;'><b>{p_code}</b><br>{p_val}%</div>", unsafe_allow_html=True)
                        
        with tab_news:
            st.markdown("### 📢 YCH Group Corporate News & Announcement Center")
            
            curr_time_str = datetime.now().strftime("%Y-%m-%d")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, category, content, date_posted, file_path 
                FROM announcements 
                WHERE expiry_date IS NULL OR expiry_date = '' OR expiry_date >= ? 
                ORDER BY id DESC
            """, (curr_time_str,))
            notices = cursor.fetchall()
            conn.close()
            
            if not notices:
                st.caption("_No active corporate announcements posted in the ledger currently._")
            else:
                for title, cat, content, dt, f_path in notices:
                    with st.container(border=True):
                        st.markdown(f"#### {title}")
                        st.markdown(f"<span style='background-color:#E2E8F0; padding:3px 8px; border-radius:12px; font-size:12px; font-weight:bold; color:#003366;'>{cat}</span> | <span style='font-size:12px; color:gray;'>Posted on {dt}</span>", unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.write(content)
                        if f_path and os.path.exists(f_path):
                            with open(f_path, "rb") as b_stream:
                                st.download_button(label=f"📎 Download Memo ({os.path.basename(f_path)})", data=b_stream.read(), file_name=os.path.basename(f_path), key=f"dl_ann_{dt}_{title}")

    # --- WORKSPACE 2: EMPLOYEE REGISTRATION ---
    elif menu == "➕ Add New Employee":
        st.markdown("### ➕ Roster New Workforce Profile")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT manager_name FROM managers ORDER BY manager_name ASC")
        manager_options = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        with st.form("master_reg_form_v2", clear_on_submit=True):
            input_emp_id = st.text_input("Employee ID Number Code:", placeholder="Format: SG0001").strip().upper()
            input_name = st.text_input("Candidate Full Name:")
            input_mobile = st.text_input("Mobile Number (Numbers only, e.g. 639123456789):").strip()
            input_gender = st.selectbox("Gender:", ["Male", "Female"])
            
            # --- NEW BIRTHDAY FIELD ---
            input_birthday = st.date_input("Date of Birth:", min_value=datetime(1950, 1, 1), max_value=datetime.now())
            
            input_dept = st.selectbox("Department:", YCH_DEPARTMENTS)
            input_role = st.text_input("Job Position:")
            
            input_manager = st.selectbox("Reporting Manager:", manager_options) if manager_options else "No Manager Assigned"
            input_date_picker = st.date_input("Start Date:")
            uploaded_pic = st.file_uploader("Employee Photo:", type=["png", "jpg", "jpeg"])
            
            if st.form_submit_button("Deploy Onboarding Track", type="primary"):
                clean_mob = re.sub(r'\D', '', input_mobile)
                
                # --- MANAGER REQUIREMENT VALIDATION ---
                if input_manager == "No Manager Assigned" or not manager_options:
                    st.error("Validation Failed: An Assigned Reporting Manager is required! Please add one in 'System Administration' first.")
                elif not re.match(r"^[A-Z]{2}[0-9]{4}$", input_emp_id):
                    st.error("Validation Failed: ID must be 2 Letters + 4 Numbers.")
                elif input_name == "" or len(clean_mob) < 8:
                    st.error("Validation Failed: Check missing fields or mobile length.")
                else:
                    photo_save_path = None
                    if uploaded_pic is not None:
                        os.makedirs("employee_photos", exist_ok=True)
                        photo_save_path = f"employee_photos/{input_emp_id}_{uploaded_pic.name}"
                        with open(photo_save_path, "wb") as f:
                            f.write(uploaded_pic.getbuffer())

                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("""
                            INSERT INTO new_hires (employee_id, mobile_number, name, role, department, manager, start_date, gender, birthday, photo_path) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (input_emp_id, input_mobile, input_name, input_role, input_dept, 
                              input_manager, input_date_picker.strftime("%B %d, %Y"), input_gender, input_birthday.strftime("%B %d, %Y"), photo_save_path))
                        new_id = cursor.lastrowid
                        
                        cursor.execute("INSERT INTO user_accounts (employee_id, password, role_type, force_password_change) VALUES (?, 'YCH1234', 'Employee', 1)", (input_emp_id,))
                        
                        default_tasks = [
                            ("Contract Signing", "Phase 1: Pre-boarding Checklist", "HR Team"),
                            ("Declaration Form Submission", "Phase 1: Pre-boarding Checklist", "HR Team"),
                            ("Familiarization Orientation Briefing", "Phase 1: Pre-boarding Checklist", "HR Team"),
                            ("Accountability Form Completion", "Phase 1: Pre-boarding Checklist", "HR Team"),
                            ("HR Onboarding Documentation Processing", "Phase 2: Day 1 Checklist", "HR Team"),
                            ("Security Training and Warehouse Entry Processing", "Phase 2: Day 1 Checklist", "Security Team"),
                            ("QA&EHS Training and Safety Protocol Review", "Phase 2: Day 1 Checklist", "QA&EHS Team"),
                            ("PPE issuance completed", "Phase 2: Day 1 Checklist", "QA&EHS Team"),
                            ("SOP Orientation Completed", "Phase 3: Technical Training Checklist", "Ops Team"),
                            ("Work Instruction Training Completed", "Phase 3: Technical Training Checklist", "Ops Team"),
                            ("Equipment Handling Training Completed", "Phase 3: Technical Training Checklist", "QA&EHS Team"),
                            ("Warehouse Operations Training Completed", "Phase 3: Technical Training Checklist", "Ops Team"),
                            ("Safety Procedures Training Completed", "Phase 3: Technical Training Checklist", "QA&EHS Team"),
                            ("Employee understands job responsibilities", "Phase 4: Performance Assessment Checklist", "HR Team"),
                            ("Employee understands account operations", "Phase 4: Performance Assessment Checklist", "HR Team"),
                            ("Employee introduced to operations team", "Phase 5: Employee Engagement & Follow-up Checklist", "HR Team")
                        ]
                        for t_name, p_name, own in default_tasks:
                            cursor.execute("INSERT INTO tasks (hire_id, task_name, phase, assigned_to) VALUES (?, ?, ?, ?)", (new_id, t_name, p_name, own))
                        
                        conn.commit()
                        st.success(f"🎉 Success: Employee {input_name} ({input_emp_id}) added alongside all roadmap tasks!")
                        
                        st.markdown("#### 📲 Send Credentials")
                        wa_msg = f"Welcome to YCH! Your account is ready.\n\nID: {input_emp_id}\nPass: YCH1234\n\nPlease login and update your password."
                        wa_link = f"https://wa.me/{clean_mob}?text={urllib.parse.quote(wa_msg)}"
                        st.markdown(f'<a href="{wa_link}" target="_blank"><button style="width:100%; padding:10px; background-color:#25D366; color:white; border:none; border-radius:5px; font-weight:bold;">📲 Click to Send WhatsApp Credentials</button></a>', unsafe_allow_html=True)
                        
                    except sqlite3.IntegrityError:
                        st.error("Error: This Employee ID already exists inside system memory.")
                    finally:
                        conn.close()

    # --- WORKSPACE 3: CHECKLIST VIEW & EDIT PROFILE ---
    elif menu == "📋 Task Checklist View":
        st.markdown("### 📋 Phased Checklist Processing & Verification Layer")
        
        # 🟢 Display Success Message here so it persists after page reload
        if st.session_state.get("profile_updated"):
            st.success("✅ Employee profile information has been successfully saved and updated!")
            st.session_state["profile_updated"] = False
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, employee_id, name, phase3_approved, phase4_approved, phase5_approved FROM new_hires WHERE status = 'Active'")
        active_dataset = cursor.fetchall()
        conn.close()
        
        if not active_dataset:
            st.info("No active employee tracking profiles detected.")
        else:
            employee_dict = {f"[{emp[1]}] {emp[2]}": emp[0] for emp in active_dataset}
            sel_worker = st.selectbox("Select an employee to manage:", list(employee_dict.keys()))
            sel_id = employee_dict[sel_worker]
            worker_record = [a for a in active_dataset if a[0] == sel_id][0]
            p3_app, p4_app, p5_app = worker_record[3], worker_record[4], worker_record[5]
            
            # --- FIXED EDIT EMPLOYEE PROFILE SECTION ---
            with st.expander("✏️ Edit Employee Profile Information"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT name, mobile_number, role, department, manager, gender, birthday, status FROM new_hires WHERE id = ?", (sel_id,))
                emp_details = cursor.fetchone()
                cursor.execute("SELECT manager_name FROM managers ORDER BY manager_name ASC")
                all_mgrs = [r[0] for r in cursor.fetchall()]
                conn.close()
                
                if emp_details:
                    with st.form("edit_profile_form"):
                        e_name = st.text_input("Full Name", value=emp_details[0])
                        e_mobile = st.text_input("Mobile Number", value=emp_details[1])
                        e_role = st.text_input("Role", value=emp_details[2])
                        
                        try:
                            dept_idx = YCH_DEPARTMENTS.index(emp_details[3])
                        except ValueError:
                            dept_idx = 0
                        e_dept = st.selectbox("Department", YCH_DEPARTMENTS, index=dept_idx)
                        
                        # 🟢 Handle manager selection safely WITH index parameter fixed
                        mgr_idx = 0
                        if emp_details[4] in all_mgrs:
                            mgr_idx = all_mgrs.index(emp_details[4])
                        e_mgr = st.selectbox("Reporting Manager", all_mgrs, index=mgr_idx) if all_mgrs else "No Manager Assigned"
                        
                        # Parse birthday back to date object safely
                        try:
                            bday_val = datetime.strptime(emp_details[6], "%B %d, %Y").date() if emp_details[6] else datetime(1990, 1, 1).date()
                        except:
                            bday_val = datetime(1990, 1, 1).date()
                        e_bday = st.date_input("Birthday", value=bday_val, min_value=datetime(1950, 1, 1), max_value=datetime.now())
                        
                        if st.form_submit_button("💾 Save Changes", type="primary"):
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE new_hires 
                                SET name = ?, mobile_number = ?, role = ?, department = ?, manager = ?, birthday = ?
                                WHERE id = ?
                            """, (e_name, e_mobile, e_role, e_dept, e_mgr, e_bday.strftime("%B %d, %Y"), sel_id))
                            conn.commit()
                            conn.close()
                            
                            # 🟢 Set session state flag instead of wiping the success message instantly
                            st.session_state["profile_updated"] = True
                            st.rerun()

            left_pane, right_pane = st.columns([2, 1])
            with left_pane:
                with st.expander("➕ Add Custom Task to This Employee", expanded=False):
                    with st.form("add_custom_task_form", clear_on_submit=True):
                        new_task_name = st.text_input("Task Name:", placeholder="e.g. Submit BIR Form 2316")
                        new_task_phase = st.selectbox("Assign to Phase:", PHASE_GROUPS)
                        new_task_team = st.selectbox("Ownership Action Team Role:", AVAILABLE_TEAMS)
                        
                        if st.form_submit_button("Incorporate Task into Checklist"):
                            if new_task_name.strip() == "":
                                st.error("Please enter a task name.")
                            else:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO tasks (hire_id, task_name, phase, assigned_to, is_completed) VALUES (?, ?, ?, ?, 0)", (sel_id, new_task_name, new_task_phase, new_task_team))
                                conn.commit()
                                conn.close()
                                st.success(f"🎉 '{new_task_name}' added to {new_task_phase.split(':')[0]}!")
                                st.rerun()

                conn = get_db_connection()
                cursor = conn.cursor()
                for step_num, phase_str in enumerate(PHASE_GROUPS, start=1):
                    st.markdown(f"#### {phase_str}")
                    is_locked = False
                    if step_num == 3 and p3_app: is_locked = True
                    if step_num == 4 and p4_app: is_locked = True
                    if step_num == 5 and p5_app: is_locked = True
                    if is_locked: st.warning("🔒 This phase has been locked by management sign-off approval.")
                    
                    cursor.execute("SELECT id, task_name, assigned_to, is_completed FROM tasks WHERE hire_id = ? AND phase = ?", (sel_id, phase_str))
                    rows = cursor.fetchall()
                    for t_id, t_name, team, comp in rows:
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            checked = st.checkbox(f"**{t_name}** `[{team}]`", value=bool(comp), key=f"t_line_{t_id}", disabled=is_locked)
                            if checked != bool(comp) and not is_locked:
                                cursor.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (1 if checked else 0, t_id))
                                conn.commit()
                                st.rerun()
                        with c2:
                            if st.button("🗑️ Drop", key=f"drop_{t_id}", disabled=is_locked):
                                cursor.execute("DELETE FROM tasks WHERE id = ?", (t_id,))
                                conn.commit()
                                st.rerun()
                    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                conn.close()
                
            with right_pane:
                st.markdown("#### 📂 Signed Documents Vault")
                with st.form("vault_upload_form", clear_on_submit=True):
                    doc_title_input = st.text_input("Document Name / Description:", placeholder="e.g. Signed Employment Contract")
                    uploaded_doc_file = st.file_uploader("Upload Signed Document (.pdf, .png, .jpg):", type=["pdf", "png", "jpg", "jpeg"])
                    if st.form_submit_button("🔒 Upload to Vault") and doc_title_input != "" and uploaded_doc_file is not None:
                        os.makedirs("vault", exist_ok=True)
                        clean_filename = f"vault/{sel_id}_{int(datetime.now().timestamp())}_{uploaded_doc_file.name}"
                        with open(clean_filename, "wb") as f: f.write(uploaded_doc_file.getbuffer())
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO signed_documents (hire_id, doc_name, file_path, date_uploaded) VALUES (?, ?, ?, ?)", 
                                       (sel_id, doc_title_input, clean_filename, datetime.now().strftime("%Y-%m-%d")))
                        conn.commit()
                        conn.close()
                        st.success("Document uploaded!")
                        st.rerun()
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id, doc_name, file_path FROM signed_documents WHERE hire_id = ?", (sel_id,))
                saved_docs = cursor.fetchall()
                conn.close()
                
                if saved_docs:
                    st.markdown("##### 📁 Archived Logs")
                    for d_id, d_name, d_path in saved_docs:
                        if os.path.exists(d_path):
                            with open(d_path, "rb") as file_bytes:
                                st.download_button(label=f"📥 {d_name}", data=file_bytes.read(), file_name=os.path.basename(d_path), key=f"dl_vdoc_{d_id}", use_container_width=True)
                st.markdown("<hr>", unsafe_allow_html=True)

                st.markdown("#### 🛡️ Manager Sign-off Portal")
                
                # Check if any documents are uploaded before allowing approval
                has_docs = len(saved_docs) > 0
                if not has_docs:
                    st.info("⚠️ Upload a document to the Vault first to unlock phase approvals.")

                conn = get_db_connection()
                cursor = conn.cursor()
                
                def render_signed_off(text):
                    st.markdown(f"<div style='background-color: #EAF4EB; color: #1E8E3E; padding: 12px; border-radius: 8px; margin-bottom: 10px; display: flex; align-items: center;'><span style='font-size: 18px; margin-right: 10px;'>✔️</span> <b>{text}</b></div>", unsafe_allow_html=True)

                if not p3_app:
                    if st.button("✅ Approve Phase 3", use_container_width=True, disabled=not has_docs):
                        cursor.execute("UPDATE new_hires SET phase3_approved = 1 WHERE id = ?", (sel_id,))
                        conn.commit(); st.rerun()
                else: 
                    render_signed_off("Phase 3 Signed Off")
                    
                if not p4_app:
                    if st.button("✅ Approve Phase 4", use_container_width=True, disabled=not has_docs):
                        cursor.execute("UPDATE new_hires SET phase4_approved = 1 WHERE id = ?", (sel_id,))
                        conn.commit(); st.rerun()
                else: 
                    render_signed_off("Phase 4 Signed Off")
                    
                if not p5_app:
                    if st.button("✅ Approve Phase 5", use_container_width=True, disabled=not has_docs):
                        cursor.execute("UPDATE new_hires SET phase5_approved = 1 WHERE id = ?", (sel_id,))
                        conn.commit(); st.rerun()
                else: 
                    render_signed_off("Phase 5 Signed Off")
                conn.close()

    # --- WORKSPACE: RULES AND GUIDELINES ---
    elif menu == "📚 Rules and Guidelines":
        st.markdown("### 📚 SOP and Manual")
        tab_view, tab_upload = st.tabs(["📖 Training Materials Repository", "📤 Upload New Learning Asset"])
        
        with tab_view:
            sel_phase = st.selectbox("Filter Assets by Lifecycle Phase Context:", PHASE_GROUPS)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, doc_type, file_path FROM lms_materials WHERE phase = ?", (sel_phase,))
            items = cursor.fetchall()
            conn.close()
            
            if not items: 
                st.info("No training modules assigned yet.")
            else:
                for lms_id, title, d_type, f_path in items: 
                    with st.container(border=True):
                        c_item, c_actions = st.columns([4, 1])
                        with c_item:
                            st.markdown(f"📄 **{title}** `[{d_type}]`")
                            if f_path and os.path.exists(f_path):
                                with open(f_path, "rb") as file_bytes:
                                    st.download_button(label=f"📥 Download {title}", data=file_bytes.read(), file_name=os.path.basename(f_path), key=f"dl_admin_lms_{lms_id}")
                        with c_actions:
                            if st.button("🗑️ Delete Asset", key=f"del_lms_{lms_id}", use_container_width=True):
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM lms_materials WHERE id = ?", (lms_id,))
                                conn.commit()
                                conn.close()
                                st.success("Asset completely removed.")
                                st.rerun()
                    
        with tab_upload:
            with st.form("lms_upload_form", clear_on_submit=True):
                asset_title = st.text_input("Module Training Document Title:")
                asset_phase = st.selectbox("Link Material to Target Phase:", PHASE_GROUPS)
                asset_type = st.selectbox("Document Classification Type:", ["SOP PDF", "Work Instruction", "Safety Manual", "Training Guidelines"])
                uploaded_lms_file = st.file_uploader("Upload Training Document (.pdf, .png, .jpg, .docx):", type=["pdf", "png", "jpg", "jpeg", "docx"])
                
                if st.form_submit_button("Deploy Training Checklist", type="primary"):
                    if asset_title.strip() == "": st.error("Validation Failed: Please enter a descriptive title.")
                    elif uploaded_lms_file is None: st.error("Validation Failed: Uploading a file attachment is strictly mandatory.")
                    else:
                        os.makedirs("lms_vault", exist_ok=True)
                        saved_file_path = f"lms_vault/{int(datetime.now().timestamp())}_{uploaded_lms_file.name}"
                        with open(saved_file_path, "wb") as f_out: f_out.write(uploaded_lms_file.getbuffer())
                        
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO lms_materials (phase, title, doc_type, file_path) VALUES (?, ?, ?, ?)", (asset_phase, asset_title, asset_type, saved_file_path))
                        conn.commit()
                        conn.close()
                        st.success(f"🎉 Success: deployed '{asset_title}' document asset node cleanly!")
                        st.rerun()

    elif menu == "📤 Export Reports":
        st.markdown("### 📤 Multi-Roster Extraction & Executive Reports Engine")
        conn = get_db_connection()
        df_exec = pd.read_sql_query("SELECT employee_id, name, mobile_number, department, role, manager, start_date, status FROM new_hires", conn)
        conn.close()
        if df_exec.empty: st.info("No compiled employee logs detected.")
        else:
            st.markdown("#### 📈 Operational Dashboard Breakdown")
            ec1, ec2 = st.columns(2)
            with ec1:
                fig_dept = px.pie(df_exec, names="department", title="Breakdown by Corporate Account Cluster", hole=0.4, color_discrete_sequence=px.colors.sequential.YlGnBu)
                st.plotly_chart(fig_dept, use_container_width=True)
            with ec2:
                fig_hours = px.histogram(df_exec, x="department", title="Candidate Counts Distributed Across Active Accounts", color_discrete_sequence=["#003366"])
                st.plotly_chart(fig_hours, use_container_width=True)
            
            st.markdown("#### 📥 Data Export")
            target_dataset_selection = st.selectbox("Select Target Segment Context:", ["Active Roster", "Archived Roster", "Complete Master List"])
            conn = get_db_connection()
            base_cmd = "SELECT employee_id, name, mobile_number, gender, birthday, department, role, manager, start_date, status FROM new_hires"
            if "Active" in target_dataset_selection: base_cmd += " WHERE status = 'Active'"; fn = "active_employees.xlsx"
            elif "Archived" in target_dataset_selection: base_cmd += " WHERE status = 'Archived'"; fn = "archived_employees.xlsx"
            else: fn = "all_employees.xlsx"
            df_out = pd.read_sql_query(base_cmd, conn)
            conn.close()
            df_out.columns = ["Employee ID", "Full Name", "Mobile Number", "Gender", "Birthday", "Department", "Position", "Reporting Manager", "Start Date", "Status"]
            ex_stream = io.BytesIO()
            with pd.ExcelWriter(ex_stream, engine='openpyxl') as writer: df_out.to_excel(writer, index=False, sheet_name='YCH_Roster_Audit')
            st.download_button(label=f"📥 Download Selected Spreadsheet ({fn})", data=ex_stream.getvalue(), file_name=fn, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="primary")

    # --- WORKSPACE 9: SYSTEM ADMINISTRATION CONTROL PANEL ---
    elif menu == "🚨 System Administration":
        st.markdown("### 🚨 System Administration")
        
        if st.session_state.get("ann_posted_success", False):
            st.success("🎉 Success: Announcement notice published live to the workspace bulletin successfully!")
            st.session_state["ann_posted_success"] = False
        
        adm_c1, adm_c2 = st.columns([1, 1], gap="large")
        with adm_c1:
            st.markdown("#### 🔍 Debug: View All Accounts")
            if st.button("List All User Accounts", use_container_width=True):
                conn = get_db_connection()
                df_users = pd.read_sql_query("SELECT employee_id, role_type FROM user_accounts", conn)
                st.dataframe(df_users, use_container_width=True)
                conn.close()
            
            st.markdown("#### ➕ Create New Admin Account")
            with st.form("new_admin_form", clear_on_submit=True):
                new_admin_id = st.text_input("New Admin Username/ID:").strip().upper()
                new_admin_pass = st.text_input("New Admin Password:", type="password")
                if st.form_submit_button("Create Admin"):
                    if new_admin_id and new_admin_pass:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            cursor.execute("INSERT INTO user_accounts (employee_id, password, role_type, force_password_change) VALUES (?, ?, 'Employer', 0)", (new_admin_id, new_admin_pass))
                            conn.commit()
                            st.success(f"Admin '{new_admin_id}' created successfully!")
                        except sqlite3.IntegrityError: st.error("Admin ID already exists.")
                        conn.close()
                        st.rerun()
                        
            st.markdown("#### 👤 Manage Operation Managers")
            with st.form("admin_m_form_v2", clear_on_submit=True):
                new_manager = st.text_input("Register New Operation Manager / PIC:")
                if st.form_submit_button("➕ Save Manager to System") and new_manager != "":
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO managers (manager_name) VALUES (?)", (new_manager.strip(),))
                        conn.commit()
                        st.success("Operational authority logged successfully.")
                    except sqlite3.IntegrityError: st.error("Entry already exists.")
                    conn.close()
                    st.rerun()
            
            # --- REMOVE MANAGER FEATURE ---
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, manager_name FROM managers ORDER BY manager_name ASC")
            existing_managers = cursor.fetchall()
            conn.close()
            
            if existing_managers:
                with st.form("remove_mgr_form"):
                    mgr_dict = {m[1]: m[0] for m in existing_managers}
                    mgr_to_remove = st.selectbox("Select Manager to Remove:", list(mgr_dict.keys()))
                    if st.form_submit_button("🗑️ Remove Manager"):
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM managers WHERE id = ?", (mgr_dict[mgr_to_remove],))
                        conn.commit()
                        conn.close()
                        st.success(f"Manager '{mgr_to_remove}' has been removed from the system.")
                        st.rerun()

        with adm_c2:
            st.markdown("#### 📢 Post Corporate Announcement")
            with st.form("ann_form", clear_on_submit=True):
                a_title = st.text_input("Announcement Title Heading:", key="txt_title")
                a_cat = st.selectbox("Target Classification Group:", ["HR Memo", "Safety Reminder", "Company Event", "Training Notice", "Policy Update"], key="sel_cat")
                a_body = st.text_area("Announcement Description Body Content:", key="txt_body")
                a_file = st.file_uploader("Attach Document Memo File (Optional):", type=["pdf", "png", "jpg", "jpeg"], key="file_attach")
                
                has_expiry = st.checkbox("Set an expiration date for this post?", key="chk_expiry")
                expiry_date_picker = st.date_input("Optional Expiration Date:", min_value=datetime.now(), key="dt_expiry")
                
                if st.form_submit_button("📢 Publish Notice", type="primary"):
                    if a_title.strip() == "": st.error("Validation Failed: Announcement requires a Title Heading.")
                    else:
                        expiry_date_val = expiry_date_picker.strftime("%Y-%m-%d") if has_expiry else ""
                        saved_ann_file = None
                        if a_file is not None:
                            os.makedirs("attachments", exist_ok=True)
                            saved_ann_file = f"attachments/{int(datetime.now().timestamp())}_{a_file.name}"
                            with open(saved_ann_file, "wb") as f_out: f_out.write(a_file.getbuffer())
                        
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO announcements (title, category, content, date_posted, file_path, expiry_date) VALUES (?, ?, ?, ?, ?, ?)", 
                                       (a_title, a_cat, a_body, datetime.now().strftime("%B %d, %Y"), saved_ann_file, expiry_date_val))
                        conn.commit()
                        conn.close()
                        st.session_state["ann_posted_success"] = True
                        st.rerun()

            st.markdown("#### ⚙️ Manage Published Bulletins")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, date_posted FROM announcements ORDER BY id DESC")
            all_notices_list = cursor.fetchall()
            conn.close()
            
            if not all_notices_list:
                st.caption("No published bulletins found.")
            else:
                for n_id, n_title, n_date in all_notices_list:
                    cn_text, cn_btn = st.columns([3, 1])
                    with cn_text: st.markdown(f"• **{n_title}** — _({n_date})_")
                    with cn_btn:
                        if st.button("🗑️ Delete Notice", key=f"del_ann_node_{n_id}", use_container_width=True):
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM announcements WHERE id = ?", (n_id,))
                            conn.commit()
                            conn.close()
                            st.success("Notice completely wiped from dashboard ledger.")
                            st.rerun()
                            
            st.markdown("#### 🔑 Employee Password Override")
            with st.form("password_reset_form", clear_on_submit=True):
                target_reset_id = st.text_input("Target Employee ID to Override (e.g., SG0002):").strip().upper()
                new_target_password = st.text_input("Provide New Account Access Password:", type="password")
                
                if st.form_submit_button("🔒 Apply Password Override"):
                    if target_reset_id != "" and new_target_password != "":
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM user_accounts WHERE UPPER(employee_id) = ? AND role_type = 'Employee'", (target_reset_id,))
                        valid_emp_account = cursor.fetchone()
                        if valid_emp_account:
                            cursor.execute("UPDATE user_accounts SET password = ? WHERE UPPER(employee_id) = ?", (new_target_password, target_reset_id))
                            conn.commit(); st.success(f"Successfully overrode access security key for employee: `{target_reset_id}`!")
                        else: st.error("Target Error: No registered employee account was found matching that specific ID code string.")
                        conn.close()
                    else: st.error("Validation Error: Please fill out both target fields.")

        st.markdown("---")
        st.markdown("### 🚨 Danger Zone: Delete Roster Accounts")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, employee_id, name FROM new_hires")
        del_opts = cursor.fetchall()
        
        if not del_opts: 
            st.info("No employee records found.")
        else:
            del_dict = {f"[{h[1]}] {h[2]}": h[0] for h in del_opts}
            target_purge = st.selectbox("Select target account to erase permanently:", list(del_dict.keys()))
            
            # Checkbox bound directly to a session state key for easy reset
            st.checkbox("Confirm permanent account removal deletion.", key="delete_checkbox")
            
            # When user clicks the main delete button, trigger the confirmation mode
            if st.button("Permanently Erase Profile", type="primary"):
                if st.session_state.delete_checkbox:
                    st.session_state.confirm_delete_stage = True
                    st.session_state.target_purge_id = del_dict[target_purge]
                else:
                    st.error("Action Intercepted: You must check the confirmation box first.")
            
            # ⚠️ TWO-STEP VERIFICATION POPUP LOGIC ⚠️
            if st.session_state.confirm_delete_stage:
                st.warning("⚠️ **WARNING: ARE YOU ABSOLUTELY SURE?**\n\nThis will permanently delete the employee profile, clear their training logs, unregister their login credentials, and wipe their photo file from the disk. This action cannot be undone.")
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    if st.button("✔️ YES, DELETE PERMANENTLY", type="primary"):
                        # Process the actual deletion
                        cursor.execute("SELECT employee_id, photo_path FROM new_hires WHERE id = ?", (st.session_state.target_purge_id,))
                        row = cursor.fetchone()
                        if row:
                            tgt_emp_code = row[0]
                            tgt_photo_path = row[1] if len(row) > 1 else None
                            
                            if tgt_photo_path and os.path.exists(tgt_photo_path):
                                os.remove(tgt_photo_path)
                            
                            cursor.execute("DELETE FROM user_accounts WHERE UPPER(employee_id) = UPPER(?)", (tgt_emp_code,))
                            cursor.execute("DELETE FROM tasks WHERE hire_id = ?", (st.session_state.target_purge_id,))
                            cursor.execute("DELETE FROM new_hires WHERE id = ?", (st.session_state.target_purge_id,))
                            conn.commit()
                            
                            st.success("Profile completely purged and file deleted.")
                        
                        # Reset states to hide popup and clear checkbox
                        st.session_state.confirm_delete_stage = False
                        if "delete_checkbox" in st.session_state:
                            del st.session_state["delete_checkbox"]
                        st.session_state.target_purge_id = None
                        st.rerun()
                
                with col2:
                    if st.button("❌ CANCEL", use_container_width=True):
                        # Hide the popup and clear the checkbox if they cancel
                        st.session_state.confirm_delete_stage = False
                        if "delete_checkbox" in st.session_state:
                            del st.session_state["delete_checkbox"]
                        st.rerun()
                        
        conn.close()
