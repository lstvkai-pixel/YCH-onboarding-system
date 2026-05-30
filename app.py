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
    
    # 1. Base New Hires Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS new_hires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL DEFAULT 'N/A',
            mobile_number TEXT NOT NULL DEFAULT 'N/A',
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL DEFAULT 'HR Team',
            manager TEXT NOT NULL,
            start_date TEXT NOT NULL,
            gender TEXT NOT NULL DEFAULT 'Male',
            status TEXT NOT NULL DEFAULT 'Active',
            photo_path TEXT DEFAULT NULL,
            phase3_approved INTEGER DEFAULT 0,
            phase4_approved INTEGER DEFAULT 0,
            phase5_approved INTEGER DEFAULT 0
        )
    ''')
    
    columns_to_add = [
        ("photo_path", "TEXT DEFAULT NULL"),
        ("phase3_approved", "INTEGER DEFAULT 0"),
        ("phase4_approved", "INTEGER DEFAULT 0"),
        ("phase5_approved", "INTEGER DEFAULT 0")
    ]
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE new_hires ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass

    # 2. Detailed Historical Training Hours Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hire_id INTEGER,
            log_date TEXT NOT NULL,
            classroom_hours INTEGER DEFAULT 0,
            ojt_hours INTEGER DEFAULT 0,
            safety_hours INTEGER DEFAULT 0,
            technical_hours INTEGER DEFAULT 0,
            FOREIGN KEY(hire_id) REFERENCES new_hires(id)
        )
    ''')
    
    # 3. Tasks Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hire_id INTEGER,
            task_name TEXT NOT NULL,
            phase TEXT NOT NULL,
            assigned_to TEXT NOT NULL,
            department TEXT NOT NULL DEFAULT 'HR Team',
            is_completed INTEGER DEFAULT 0,
            FOREIGN KEY(hire_id) REFERENCES new_hires(id)
        )
    ''')

    # 4. Signed Documents Vault Storage Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signed_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hire_id INTEGER,
            doc_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            date_uploaded TEXT NOT NULL,
            FOREIGN KEY(hire_id) REFERENCES new_hires(id)
        )
    ''')
    
    # 5. LMS Modules Storage Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lms_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phase TEXT NOT NULL,
            title TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            file_path TEXT DEFAULT NULL
        )
    ''')
    
    # 6. Certification Ledger Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hire_id INTEGER,
            cert_name TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            FOREIGN KEY(hire_id) REFERENCES new_hires(id)
        )
    ''')
    
    # 7. Feedback Tickets Engine Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hire_id INTEGER,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            ticket_status TEXT NOT NULL DEFAULT 'Open',
            date_logged TEXT NOT NULL,
            FOREIGN KEY(hire_id) REFERENCES new_hires(id)
        )
    ''')
    
    # 8. Corporate Announcement Bulletin Table (Updated with attachment trace support)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            date_posted TEXT NOT NULL,
            file_path TEXT DEFAULT NULL
        )
    ''')
    try:
        cursor.execute("ALTER TABLE announcements ADD COLUMN file_path TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    
    # 9. Managers Reference List Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS managers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # System Migration Mappings
    cursor.execute("UPDATE tasks SET phase = 'Phase 1: Pre-boarding Checklist' WHERE phase LIKE 'Group 1%'")
    cursor.execute("UPDATE tasks SET phase = 'Phase 2: Day 1 Checklist' WHERE phase LIKE 'Group 2%'")
    cursor.execute("UPDATE tasks SET phase = 'Phase 5: Employee Engagement & Follow-up Checklist' WHERE phase LIKE 'Group 3%'")
    
    cursor.execute("UPDATE tasks SET assigned_to = 'Ops Team' WHERE phase LIKE 'Phase 3%' AND task_name IN ('SOP Orientation Completed', 'Work Instruction Training Completed', 'Warehouse Operations Training Completed', 'System/Application Training Completed', 'On-the-Job Training Completed')")
    cursor.execute("UPDATE tasks SET assigned_to = 'QA&EHS Team' WHERE phase LIKE 'Phase 3%' AND task_name IN ('Equipment Handling Training Completed', 'Safety Procedures Training Completed', 'Forklift Training Completed (If Applicable)', 'Technical Competency Assessment Completed')")
    
    conn.commit()
    conn.close()

init_database()

# ==========================================
# CORE CONSTANTS, THEME STRINGS & PARAMETERS
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

st.markdown("""
    <style>
        .stApp { background-color: #F8FAFC; }
        .ych-card {
            background-color: #FFFFFF;
            border-radius: 8px;
            padding: 18px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            border-left: 5px solid #003366;
            margin-bottom: 15px;
            height: 125px;
        }
        .ych-kpi-val {
            font-size: 32px; font-weight: bold; color: #003366; line-height: 1.1; margin-top: 4px;
        }
        .ych-kpi-lbl {
            font-size: 14px; color: #64748B; font-weight: 600; margin-bottom: 0px;
        }
        .ych-action-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            width: 100%;
            height: 42px;
            border: none;
            border-radius: 4px;
            color: white;
            font-weight: bold;
            font-size: 12px;
            cursor: pointer;
            text-decoration: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

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

def get_total_learning_hours(hire_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(classroom_hours + ojt_hours + safety_hours + technical_hours) FROM training_logs WHERE hire_id = ?", (hire_id,))
    res = cursor.fetchone()[0]
    conn.close()
    return res if res else 0

def evaluate_achievements(hire_id, overall, phase_data, total_hours):
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
# STREAMLIT UI CONFIGURATION & NAVIGATION
# ==========================================
st.sidebar.markdown("<h2 style='color: #003366; font-family: sans-serif; font-weight: 800; margin-bottom: 0px;'>🏢 YCH GROUP</h2>", unsafe_allow_html=True)
st.sidebar.caption("Human Resources Experience Hub")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "NAVIGATION HUB", 
    ["🏢 Corporate Experience Landing", "➕ Add New Employee", "📋 Task Checklist View", "📚 Learning Center", "🏅 Certification Center", "💬 Employee Feedback Portal", "📤 Export Reports", "🚨 System Administration"]
)

# --- WORKSPACE 1: HR CORPORATE LANDING PAGE ---
if menu == "🏢 Corporate Experience Landing":
    st.markdown("<h1 style='color: #003366; text-align: center; font-family: sans-serif; font-weight: 700;'>YCH GROUP EMPLOYEE EXPERIENCE PLATFORM</h1>", unsafe_allow_html=True)
    st.markdown("<h5 style='color: #0078D4; text-align: center; font-family: sans-serif; font-weight: 400; margin-top: -10px;'>Nurturing Talent, Driving Operational Excellence, Building Careers</h5>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.info("🤝 **Our Welcome Charter:** Welcome to YCH Group. We are committed to developing world-class logistics professionals through structured onboarding, technical excellence, safety leadership, and continuous learning.")
    st.markdown("<br>", unsafe_allow_html=True)
    
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
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(f"<div class='ych-card'><p class='ych-kpi-lbl'>Active Tracks</p><p class='ych-kpi-val'>{act_c}</p></div>", unsafe_allow_html=True)
    with k2: st.markdown(f"<div class='ych-card'><p class='ych-kpi-lbl'>Completed Onboarding</p><p class='ych-kpi-val'>{grad_c}</p></div>", unsafe_allow_html=True)
    with k3: st.markdown(f"<div class='ych-card'><p class='ych-kpi-lbl'>Avg Completion</p><p class='ych-kpi-val'>{avg_rate}%</p></div>", unsafe_allow_html=True)
    with k4: st.markdown(f"<div class='ych-card'><p class='ych-kpi-lbl'>New Hires (Month)</p><p class='ych-kpi-val'>{act_c}</p></div>", unsafe_allow_html=True)
    
    tab_dash, tab_board, tab_news = st.tabs(["📊 Active Journeys Grid", "🏆 Monthly Training Hours", "📢 Corporate News Feed"])
    
    with tab_dash:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, employee_id, name, role, department, manager, start_date, mobile_number, photo_path, phase3_approved, phase4_approved, phase5_approved FROM new_hires WHERE status = 'Active'")
        active_dataset = cursor.fetchall()
        conn.close()
        
        if not active_dataset:
            st.info("No active onboarding profiles running inside the logistics roadmap track pipelines.")
        else:
            for node in active_dataset:
                h_id, emp_id, name, role, dept, manager, start_date, mobile, photo, p3_a, p4_a, p5_a = node
                ovr_pct, p_breakdown = calculate_metrics_pipeline(h_id)
                health_state = assign_status_health(ovr_pct)
                total_h = get_total_learning_hours(h_id)
                earned_achievements = evaluate_achievements(h_id, ovr_pct, p_breakdown, total_h)
                
                with st.container(border=True):
                    dc1, dc2, dc3 = st.columns([1, 3, 2])
                    with dc1:
                        if photo and os.path.exists(photo):
                            st.image(photo, width=120)
                        else:
                            st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=120)
                    with dc2:
                        st.subheader(f"{name} ({emp_id})")
                        st.markdown(f"💼 **{role}** | 🏬 {dept} | 👤 PIC: *{manager}*")
                        st.markdown(f"📱 Contact: `{mobile}` | 📅 Started: *{start_date}*")
                        st.markdown(f"📈 Onboarding Status Health: **{health_state}**")
                        
                        if earned_achievements:
                            st.markdown(" ".join([f"<span style='background-color:#E2E8F0; padding:3px 8px; border-radius:12px; font-size:12px; margin-right:5px; font-weight:bold; color:#003366;'>{b}</span>" for b in earned_achievements]), unsafe_allow_html=True)
                    with dc3:
                        st.metric("Overall Completion Progress", f"{ovr_pct}%")
                        st.progress(ovr_pct / 100)
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        raw_channel_msg = (
                            f"🚨 *[YCH_HR Alert] New Employee Onboarding Scheduled*\n\n"
                            f"*Employee Details*\n"
                            f"• *Employee ID:* {emp_id}\n"
                            f"• *Full Name:* {name}\n"
                            f"• *Account Department:* {dept}\n"
                            f"• *Job Position:* {role}\n"
                            f"• *Reporting Manager:* {manager}\n"
                            f"• *Training Start Date:* {start_date}\n\n"
                            f"Please prepare all onboarding and training requirements accordingly."
                        )
                        encoded_channel = urllib.parse.quote(raw_channel_msg)
                        GROUP_TOKEN = "JIeWsX45KJEAWsavJUZAff"
                        channel_url = f"https://api.whatsapp.com/send?phone=&text={encoded_channel}&context={GROUP_TOKEN}"
                        
                        raw_progress_msg = (
                            f"📊 *YCH Onboarding Progress Update*\n\n"
                            f"• *Employee ID:* {emp_id}\n"
                            f"• *Name:* {name}\n\n"
                            f"📈 *Overall Completion:* {ovr_pct}%\n"
                            f"• Phase 1: {p_breakdown['Phase 1']}%\n"
                            f"• Phase 2: {p_breakdown['Phase 2']}%\n"
                            f"• Phase 3: {p_breakdown['Phase 3']}%\n"
                            f"• Phase 4: {p_breakdown['Phase 4']}%\n"
                            f"• Phase 5: {p_breakdown['Phase 5']}%\n\n"
                            f"Please continue completing the remaining onboarding requirements."
                        )
                        clean_phone = re.sub(r'\D', '', mobile)
                        encoded_progress = urllib.parse.quote(raw_progress_msg)
                        employee_sms_url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_progress}"

                        st.markdown(f"""
                            <div style='display: flex; gap: 10px; width: 100%;'>
                                <a href='{channel_url}' target='_blank' style='flex: 1; text-decoration: none;'>
                                    <button class='ych-action-btn' style='background-color: #003366;'>📢 Group Broadcast</button>
                                </a>
                                <a href='{employee_sms_url}' target='_blank' style='flex: 1; text-decoration: none;'>
                                    <button class='ych-action-btn' style='background-color: #25D366;'>📲 Send Progress</button>
                                </a>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        if ovr_pct == 100 and p3_a and p4_a and p5_a:
                            pdf_buffer = io.BytesIO()
                            doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
                            styles = getSampleStyleSheet()
                            cert_style = ParagraphStyle('Cert', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=24, leading=28, alignment=TA_CENTER, textColor='#003366')
                            body_style = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=14, leading=18, alignment=TA_CENTER, textColor='#333333')
                            
                            story = [
                                Spacer(1, 100),
                                Paragraph("YCH GROUP GRADUATION CERTIFICATE", cert_style),
                                Spacer(1, 30),
                                Paragraph(f"This document proudly certifies that", body_style),
                                Spacer(1, 15),
                                Paragraph(f"<b>{name}</b>", cert_style),
                                Spacer(1, 15),
                                Paragraph(f"has successfully completed the complete enterprise logistics onboarding track curriculum for position <b>{role}</b> inside the <b>{dept}</b> account team framework securely.", body_style),
                                Spacer(1, 40),
                                Paragraph(f"Verified Registration Key: <i>{emp_id}</i> | Date Issued: {datetime.now().strftime('%B %d, %Y')}", body_style),
                                Spacer(1, 50),
                                Paragraph("✍️ <i>YCH Group Corporate HR Management</i>", body_style)
                            ]
                            doc.build(story)
                            st.download_button(f"🎓 Download Graduation Certificate", data=pdf_buffer.getvalue(), file_name=f"ych_cert_{emp_id}.pdf", mime="application/pdf", use_container_width=True)

                    st.markdown("<br>", unsafe_allow_html=True)
                    m_cols = st.columns(5)
                    for step_idx, phase_spec in enumerate(PHASE_GROUPS):
                        p_code = phase_spec.split(":")[0]
                        p_val = p_breakdown[p_code]
                        with m_cols[step_idx]:
                            bg_lbl = "🔵" if p_val == 100 else ("🟠" if p_val > 0 else "⚪")
                            st.markdown(f"<div style='text-align:center; font-size:12px; background:#EEF2F6; padding:5px; border-radius:4px;'>{bg_lbl} <b>{p_code}</b><br>{p_val}%</div>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin:20px 0;'>", unsafe_allow_html=True)
                    
    with tab_board:
        st.subheader("📊 Monthly Training Hours Leaderboard")
        current_year_month = datetime.now().strftime("%Y-%m")
        selected_month_str = st.text_input("📆 Filter Training Month Year (YYYY-MM):", value=current_year_month)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT h.name, h.role, SUM(l.classroom_hours + l.ojt_hours + l.safety_hours + l.technical_hours) as monthly_hours 
            FROM training_logs l 
            JOIN new_hires h ON l.hire_id = h.id 
            WHERE l.log_date LIKE ? 
            GROUP BY h.id
        """, (f"{selected_month_str}%",))
        records = cursor.fetchall()
        conn.close()
        
        board_data = [{"Name": r[0], "Role": r[1], f"Training Hours ({selected_month_str})": r[2]} for r in records]
            
        if board_data:
            df_board = pd.DataFrame(board_data).sort_values(by=[f"Training Hours ({selected_month_str})"], ascending=False).head(10)
            num_rows = len(df_board)
            medals = []
            for i in range(num_rows):
                if i == 0: medals.append('🥇 Gold')
                elif i == 1: medals.append('🥈 Silver')
                elif i == 2: medals.append('🥉 Bronze')
                else: medals.append('⭐ Performer')
                
            df_board.insert(0, 'Rank Medal', medals)
            st.dataframe(df_board, use_container_width=True, hide_index=True)
        else:
            st.info(f"No training hours logged for the month: {selected_month_str}.")
            
    with tab_news:
        st.subheader("📢 YCH Group Corporate News & Announcement Center")
        conn = get_db_connection()
        cursor = conn.cursor()
        # ✅ UPGRADE: Pull file attachments if available from database layer
        cursor.execute("SELECT title, category, content, date_posted, file_path FROM announcements ORDER BY id DESC")
        notices = cursor.fetchall()
        conn.close()
        
        if not notices:
            st.caption("_No corporate announcements posted in the ledger currently._")
        else:
            for title, cat, content, dt, f_path in notices:
                st.markdown(f"##### 🔔 {title} `[{cat}]` — _Posted on {dt}_")
                st.write(content)
                
                # ✅ UPGRADE: Render direct document attachment vault links in the feed tab layer
                if f_path and os.path.exists(f_path):
                    with open(f_path, "rb") as b_stream:
                        st.download_button(label=f"📎 Download Attached Memo Document File ({os.path.basename(f_path)})", data=b_stream.read(), file_name=os.path.basename(f_path), key=f"dl_ann_{dt}_{title}")
                st.markdown("---")

# --- WORKSPACE 2: EMPLOYEE REGISTRATION ---
elif menu == "➕ Add New Employee":
    st.title("➕ Roster New Workforce Profile")
    st.markdown("---")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT manager_name FROM managers ORDER BY manager_name ASC")
    manager_options = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    with st.form("master_reg_form_v2", clear_on_submit=True):
        input_emp_id = st.text_input("Employee ID Number Code:", placeholder="Format requirement: SG0001").strip()
        input_name = st.text_input("Candidate Full Name Layout:")
        input_mobile = st.text_input("Mobile Number (Minimum 8 digits, numeric only):").strip()
        input_gender = st.selectbox("Gender:", ["Male", "Female"])
        input_dept = st.selectbox("Allocated Logistics Hub Department:", YCH_DEPARTMENTS)
        input_role = st.text_input("Job Position / Operations Title:", placeholder="e.g. Reach Truck Operator")
        input_manager = st.selectbox("Reporting Manager/PIC Option:", manager_options) if manager_options else "No Manager Assigned"
        input_date_picker = st.date_input("Start Date:")
        uploaded_pic = st.file_uploader("Upload Corporate Digital Employee Photo (.png, .jpg):", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("Deploy Onboarding Track & Format Alert"):
            clean_mob = re.sub(r'\D', '', input_mobile)
            if not re.match(r"^[A-Z]{2}[0-9]{4}$", input_emp_id):
                st.error("Validation Failed: Employee ID must follow 2 Capital Letters + 4 Numbers.")
            elif input_name == "" or len(clean_mob) < 8 or input_manager == "No Manager Assigned":
                st.error("Validation Failed: Check empty fields or length requirements.")
            else:
                saved_img_path = None
                if uploaded_pic:
                    os.makedirs("photos", exist_ok=True)
                    saved_img_path = f"photos/{input_emp_id}_{uploaded_pic.name}"
                    with open(saved_img_path, "wb") as f:
                        f.write(uploaded_pic.getbuffer())
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO new_hires (employee_id, mobile_number, name, role, department, manager, start_date, gender, status, photo_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)",
                               (input_emp_id, input_mobile, input_name, input_role, input_dept, input_manager, input_date_picker.strftime("%B %d, %Y"), input_gender, saved_img_path))
                new_id = cursor.lastrowid
                default_tasks = [
                    ("Contract Signing", "Phase 1: Pre-boarding Checklist", "HR Team"),
                    ("Declaration Form Submission", "Phase 1: Pre-boarding Checklist", "HR Team"),
                    ("Familiarization Orientation Briefing", "Phase 1: Pre-boarding Checklist", "HR Team"),
                    ("Accountability Form Completion", "Phase 1: Pre-boarding Checklist", "HR Team"),
                    ("HR Onboarding Documentation Processing", "Phase 2: Day 1 Checklist", "HR Team"),
                    ("Security Training and Warehouse Entry Processing", "Phase 2: Day 1 Checklist", "Security Team"),
                    ("QA&EHS Training and Safety Protocol Review", "Phase 2: Day 1 Checklist", "QA&EHS Team"),
                    ("SOP Orientation Completed", "Phase 3: Technical Training Checklist", "Ops Team"),
                    ("Work Instruction Training Completed", "Phase 3: Technical Training Checklist", "Ops Team"),
                    ("Equipment Handling Training Completed", "Phase 3: Technical Training Checklist", "QA&EHS Team"),
                    ("Warehouse Operations Training Completed", "Phase 3: Technical Training Checklist", "Ops Team"),
                    ("Safety Procedures Training Completed", "Phase 3: Technical Training Checklist", "QA&EHS Team"),
                    ("Employee understands job responsibilities", "Phase 4: Performance Assessment Checklist", "HR Team"),
                    ("Employee understands account operations", "Phase 4: Performance Assessment Checklist", "HR Team"),
                    ("Employee introduced to operations team", "Phase 5: Employee Engagement & Follow-up Checklist", "HR Team"),
                    ("PPE issuance completed", "Phase 5: Employee Engagement & Follow-up Checklist", "QA&EHS Team")
                ]
                for t_name, p_name, own in default_tasks:
                    cursor.execute("INSERT INTO tasks (hire_id, task_name, phase, assigned_to, department) VALUES (?, ?, ?, ?, ?)", (new_id, t_name, p_name, own, input_dept))
                conn.commit()
                conn.close()
                st.success("Successfully generated profile tracking layers.")
                st.rerun()

# --- WORKSPACE 3: CHECKLIST VIEW ---
elif menu == "📋 Task Checklist View":
    st.title("📋 Phased Checklist Processing & Verification Layer")
    st.markdown("---")
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
        
        left_pane, right_pane = st.columns([2, 1])
        with left_pane:
            conn = get_db_connection()
            cursor = conn.cursor()
            for step_num, phase_str in enumerate(PHASE_GROUPS, start=1):
                st.markdown(f"### 📋 {phase_str}")
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
                st.markdown("<br>", unsafe_allow_html=True)
            conn.close()
            
        with right_pane:
            st.subheader("📂 Signed Documents Vault")
            with st.form("vault_upload_form", clear_on_submit=True):
                doc_title_input = st.text_input("Document Name / Description:", placeholder="e.g. Signed Employment Contract")
                uploaded_doc_file = st.file_uploader("Upload Signed Document File (.pdf, .png, .jpg):", type=["pdf", "png", "jpg", "jpeg"])
                if st.form_submit_button("🔒 Upload Document to Vault") and doc_title_input != "" and uploaded_doc_file is not None:
                    os.makedirs("vault", exist_ok=True)
                    clean_filename = f"vault/{sel_id}_{int(datetime.now().timestamp())}_{uploaded_doc_file.name}"
                    with open(clean_filename, "wb") as f:
                        f.write(uploaded_doc_file.getbuffer())
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO signed_documents (hire_id, doc_name, file_path, date_uploaded) VALUES (?, ?, ?, ?)", 
                                   (sel_id, doc_title_input, clean_filename, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    conn.close()
                    st.success("Document uploaded securely to employee records vault!")
                    st.rerun()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, doc_name, file_path FROM signed_documents WHERE hire_id = ?", (sel_id,))
            saved_docs = cursor.fetchall()
            conn.close()
            
            if saved_docs:
                st.markdown("##### 📁 Archived Documents Vault Logs")
                for d_id, d_name, d_path in saved_docs:
                    if os.path.exists(d_path):
                        with open(d_path, "rb") as file_bytes:
                            st.download_button(label=f"📥 Download {d_name}", data=file_bytes.read(), file_name=os.path.basename(d_path), key=f"dl_vdoc_{d_id}", use_container_width=True)
            st.markdown("<hr>", unsafe_allow_html=True)

            st.subheader("🛡️ Manager Sign-off Portal")
            conn = get_db_connection()
            cursor = conn.cursor()
            if not p3_app:
                if st.button("✅ Approve Phase 3: Operations Training", use_container_width=True):
                    cursor.execute("UPDATE new_hires SET phase3_approved = 1 WHERE id = ?", (sel_id,))
                    conn.commit()
                    st.rerun()
            else: st.markdown("⚙️ _Phase 3 Operations Training Signed Off_")
            if not p4_app:
                if st.button("✅ Approve Phase 4: Performance Assessment", use_container_width=True):
                    cursor.execute("UPDATE new_hires SET phase4_approved = 1 WHERE id = ?", (sel_id,))
                    conn.commit()
                    st.rerun()
            else: st.markdown("📈 _Phase 4 Performance Evaluation Signed Off_")
            if not p5_app:
                if st.button("✅ Approve Phase 5: HR Final Confirmation", use_container_width=True):
                    cursor.execute("UPDATE new_hires SET phase5_approved = 1 WHERE id = ?", (sel_id,))
                    conn.commit()
                    st.rerun()
            else: st.markdown("🤝 _Phase 5 HR Final Validation Signed Off_")
            st.markdown("<hr>", unsafe_allow_html=True)
            
            st.subheader("⏱️ Log Training Hours Audit")
            with st.form("hours_form", clear_on_submit=True):
                log_date_picker = st.date_input("Training Session Date Context:")
                add_c = st.number_input("Add Classroom Hours:", min_value=0, step=1)
                add_o = st.number_input("Add On-the-Job (OJT) Hours:", min_value=0, step=1)
                add_s = st.number_input("Add Safety Training Hours:", min_value=0, step=1)
                add_t = st.number_input("Add Technical Training Hours:", min_value=0, step=1)
                if st.form_submit_button("Log Hours to Employee File"):
                    cursor.execute("""
                        INSERT INTO training_logs (hire_id, log_date, classroom_hours, ojt_hours, safety_hours, technical_hours) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (sel_id, log_date_picker.strftime("%Y-%m-%d"), add_c, add_o, add_s, add_t))
                    conn.commit()
                    st.success(f"🎉 Success: Logged {add_c+add_o+add_s+add_t} total training hours for this date context!")
            conn.close()

elif menu == "📚 Learning Center":
    st.title("📚 YCH Group Learning Management System (LMS)")
    st.markdown("---")
    tab_view, tab_upload = st.tabs(["📖 Training Materials Repository", "📤 Upload New Learning Asset"])
    with tab_view:
        sel_phase = st.selectbox("Filter Assets by Lifecycle Phase Context:", PHASE_GROUPS)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, doc_type FROM lms_materials WHERE phase = ?", (sel_phase,))
        items = cursor.fetchall()
        conn.close()
        if not items: st.info("No training modules assigned yet.")
        else:
            for title, d_type in items: st.markdown(f"📄 **{title}** `[{d_type}]`")
    with tab_upload:
        with st.form("lms_upload_form", clear_on_submit=True):
            asset_title = st.text_input("Module Training Document Title:")
            asset_phase = st.selectbox("Link Material to Target Phase:", PHASE_GROUPS)
            asset_type = st.selectbox("Document Classification Type:", ["SOP PDF", "Work Instruction", "Safety Manual", "Training Video Link"])
            if st.form_submit_button("Deploy Material to LMS Node") and asset_title != "":
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO lms_materials (phase, title, doc_type) VALUES (?, ?, ?)", (asset_phase, asset_title, asset_type))
                conn.commit()
                conn.close()
                st.rerun()

elif menu == "🏅 Certification Center":
    st.title("🏅 License Verification & Certification Center")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, employee_id, name FROM new_hires WHERE status = 'Active'")
    hires = cursor.fetchall()
    cursor.execute("SELECT h.employee_id, h.name, c.cert_name, c.expiry_date FROM certifications c JOIN new_hires h ON c.hire_id = h.id")
    all_certs = cursor.fetchall()
    for eid, name, cname, exp_str in all_certs:
        try:
            exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
            if exp_dt <= datetime.now() + timedelta(days=30):
                st.error(f"⚠️ **COMPLIANCE ALERT:** License `{cname}` for **{name}** ({eid}) expires on **{exp_str}**!")
        except ValueError: pass
    conn.close()
    c1, c2 = st.columns([2, 1], gap="large")
    with c1:
        st.subheader("📜 Active Certified Roster")
        if not all_certs: st.caption("_No competency certificates indexed._")
        else:
            df_c = pd.DataFrame(all_certs, columns=["Employee ID", "Full Name", "Certificate / License Name", "Expiry Date"])
            st.dataframe(df_c, use_container_width=True, hide_index=True)
    with c2:
        st.subheader("➕ Register Certificate License")
        if hires:
            h_dict = {f"[{h[1]}] {h[2]}": h[0] for h in hires}
            target_h = st.selectbox("Select Target Worker Record ID:", list(h_dict.keys()))
            c_name = st.text_input("Certificate Name:")
            i_date = st.date_input("Issue Date Validation:")
            e_date = st.date_input("Expiry Date Target Boundary:")
            if st.button("Save Certificate to File", use_container_width=True) and c_name != "":
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO certifications (hire_id, cert_name, issue_date, expiry_date) VALUES (?, ?, ?, ?)", (h_dict[target_h], c_name, i_date.strftime("%Y-%m-%d"), e_date.strftime("%Y-%m-%d")))
                conn.commit()
                conn.close()
                st.rerun()

elif menu == "💬 Employee Feedback Portal":
    st.title("💬 Interactive Employee Engagement & Feedback Workflow")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, employee_id, name FROM new_hires WHERE status = 'Active'")
    hires = cursor.fetchall()
    conn.close()
    f_pane, a_pane = st.columns([1, 1], gap="large")
    with f_pane:
        st.subheader("📝 Submit Workspace Feedback")
        if hires:
            h_dict = {f"[{h[1]}] {h[2]}": h[0] for h in hires}
            f_owner = st.selectbox("Identify Your Candidate Record Token:", list(h_dict.keys()), key="f_owner")
            f_cat = st.selectbox("Feedback Ticket Category classification:", ["Safety", "Operations", "Training", "HR", "Workplace"])
            f_text = st.text_area("Type description data or suggestion ideas:")
            if st.button("Deploy Feedback Ticket", use_container_width=True) and f_text != "":
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO feedback_tickets (hire_id, category, content, ticket_status, date_logged) VALUES (?, ?, ?, 'Open', ?)", (h_dict[f_owner], f_cat, f_text, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                conn.close()
                st.rerun()
    with a_pane:
        st.subheader("🛡️ Administrative Triage Control")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT t.id, h.name, t.category, t.content, t.ticket_status FROM feedback_tickets t JOIN new_hires h ON t.hire_id = h.id WHERE t.ticket_status = 'Open'")
        open_tickets = cursor.fetchall()
        if not open_tickets: st.info("All cases have been resolved.")
        else:
            for tid, hname, category, body, stat in open_tickets:
                with st.container(border=True):
                    st.markdown(f"**From Worker:** {hname} | **Category:** `{category}`")
                    st.write(f'"{body}"')
                    if st.button(f"🔒 Close Ticket Key #{tid}", key=f"cls_{tid}"):
                        cursor.execute("UPDATE feedback_tickets SET ticket_status = 'Closed' WHERE id = ?", (tid,))
                        conn.commit()
                        st.rerun()
        conn.close()

elif menu == "📤 Export Reports":
    st.title("📤 Multi-Roster Extraction & Executive Reports Engine")
    conn = get_db_connection()
    df_exec = pd.read_sql_query("SELECT employee_id, name, mobile_number, department, role, manager, start_date, status FROM new_hires", conn)
    conn.close()
    if df_exec.empty: st.info("No compiled employee logs detected.")
    else:
        st.subheader("📈 Operational Dashboard Breakdown")
        ec1, ec2 = st.columns(2)
        with ec1:
            fig_dept = px.pie(df_exec, names="department", title="Breakdown by Corporate Account Cluster", hole=0.4, color_discrete_sequence=px.colors.sequential.YlGnBu)
            st.plotly_chart(fig_dept, use_container_width=True)
        with ec2:
            fig_hours = px.histogram(df_exec, x="department", title="Candidate Counts Distributed Across Active Accounts", color_discrete_sequence=["#003366"])
            st.plotly_chart(fig_hours, use_container_width=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        target_dataset_selection = st.selectbox("Select Target Segment Context:", ["Active Roster", "Archived Roster", "Complete Master List"])
        conn = get_db_connection()
        base_cmd = "SELECT employee_id, name, mobile_number, gender, department, role, manager, start_date, status FROM new_hires"
        if "Active" in target_dataset_selection: base_cmd += " WHERE status = 'Active'"; fn = "active_employees.xlsx"
        elif "Archived" in target_dataset_selection: base_cmd += " WHERE status = 'Archived'"; fn = "archived_employees.xlsx"
        else: fn = "all_employees.xlsx"
        df_out = pd.read_sql_query(base_cmd, conn)
        conn.close()
        df_out.columns = ["Employee ID", "Full Name", "Mobile Number", "Gender", "Department", "Position", "Reporting Manager", "Start Date", "Status"]
        ex_stream = io.BytesIO()
        with pd.ExcelWriter(ex_stream, engine='openpyxl') as writer:
            df_out.to_excel(writer, index=False, sheet_name='YCH_Roster_Audit')
        st.download_button(label=f"📥 Download Selected Spreadsheet ({fn})", data=ex_stream.getvalue(), file_name=fn, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

# --- WORKSPACE 9: SYSTEM ADMINISTRATION CONTROL PANEL ---
elif menu == "🚨 System Administration":
    st.title("🚨 Enterprise Control Room & System Administration")
    adm_c1, adm_c2 = st.columns([1, 1], gap="large")
    with adm_c1:
        st.subheader("👤 Managers Masterlist Validation Options")
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
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Reference layout: image_686fa7.png
        st.subheader("📢 Post Corporate Announcement Bulletin")
        with st.form("ann_form", clear_on_submit=False):
            a_title = st.text_input("Announcement Title Heading:")
            a_cat = st.selectbox("Target Classification Group:", ["Safety Reminder", "Company Event", "Training Notice", "Policy Update"])
            a_body = st.text_area("Announcement Description Body Content:")
            
            # ✅ NEW: Document/Image uploader added inside the bulletin creator form block
            a_file = st.file_uploader("Attach Document Memo File / Image (Optional):", type=["pdf", "png", "jpg", "jpeg"])
            
            if st.form_submit_button("📢 Publish Notice to Workspace") and a_title != "":
                saved_ann_file = None
                if a_file is not None:
                    os.makedirs("attachments", exist_ok=True)
                    saved_ann_file = f"attachments/{int(datetime.now().timestamp())}_{a_file.name}"
                    with open(saved_ann_file, "wb") as f_out:
                        f_out.write(a_file.getbuffer())
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO announcements (title, category, content, date_posted, file_path) VALUES (?, ?, ?, ?, ?)", 
                               (a_title, a_cat, a_body, datetime.now().strftime("%B %d, %Y"), saved_ann_file))
                conn.commit()
                conn.close()
                st.success("🎉 Bulletin notice with attached file published live successfully!")
                st.rerun()
    with adm_c2:
        st.subheader("🚨 Danger Zone: Purge Roster Accounts")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, employee_id, name FROM new_hires")
        del_opts = cursor.fetchall()
        if not del_opts: st.info("No employee records found.")
        else:
            del_dict = {f"[{h[1]}] {h[2]}": h[0] for h in del_opts}
            target_purge = st.selectbox("Select target account to erase permanently:", list(del_dict.keys()))
            p_check = st.checkbox("Confirm permanent account removal deletion.")
            if st.button("Permanently Erase Profile", type="primary") and p_check:
                cursor.execute("DELETE FROM tasks WHERE hire_id = ?", (del_dict[target_purge],))
                cursor.execute("DELETE FROM new_hires WHERE id = ?", (del_dict[target_purge],))
                conn.commit()
                st.success("Purged out completely.")
                st.rerun()
        conn.close()
