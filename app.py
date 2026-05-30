import sqlite3
import streamlit as st
import urllib.parse
import re
import pandas as pd
import io

# ==========================================
# DATABASE BACKEND LOGIC (The Engine)
# ==========================================
def get_db_connection():
    return sqlite3.connect("onboarding.db")

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. New Hires Table
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
            status TEXT NOT NULL DEFAULT 'Active'
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE new_hires ADD COLUMN mobile_number TEXT NOT NULL DEFAULT 'N/A'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE new_hires ADD COLUMN status TEXT NOT NULL DEFAULT 'Active'")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE new_hires ADD COLUMN gender TEXT NOT NULL DEFAULT 'Male'")
    except sqlite3.OperationalError:
        pass
    
    # 2. Tasks Table
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
    
    # System Migration Mappings
    cursor.execute("UPDATE tasks SET phase = 'Phase 1: Pre-boarding Checklist' WHERE phase LIKE 'Group 1%'")
    cursor.execute("UPDATE tasks SET phase = 'Phase 2: Day 1 Checklist' WHERE phase LIKE 'Group 2%'")
    cursor.execute("UPDATE tasks SET phase = 'Phase 5: Employee Engagement & Follow-up Checklist' WHERE phase LIKE 'Group 3%'")
    
    # 3. Managers Masterlist Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS managers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_name TEXT NOT NULL UNIQUE
        )
    ''')
    
    conn.commit()
    conn.close()

init_database()

# ==========================================
# CONFIGURATION CONSTANTS & ENUMS
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
# SYSTEM WORKFLOW HELPER UTILITIES
# ==========================================
def generate_whatsapp_message(emp_id, name, dept, role, manager, start_date):
    return (
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

def calculate_completion_metrics(hire_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*), SUM(is_completed) FROM tasks WHERE hire_id = ?", (hire_id,))
    total_tasks, completed_tasks = cursor.fetchone()
    completed_tasks = completed_tasks if completed_tasks else 0
    overall_pct = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    
    phase_metrics = {}
    for phase in PHASE_GROUPS:
        cursor.execute("SELECT COUNT(*), SUM(is_completed) FROM tasks WHERE hire_id = ? AND phase = ?", (hire_id, phase))
        p_tot, p_comp = cursor.fetchone()
        p_comp = p_comp if p_comp else 0
        p_pct = int((p_comp / p_tot) * 100) if p_tot > 0 else 0
        phase_metrics[phase.split(":")[0]] = p_pct
        
    conn.close()
    return overall_pct, phase_metrics, total_tasks, completed_tasks

# ==========================================
# STREAMLIT UI CONFIGURATION & NAVIGATION
# ==========================================
st.set_page_config(page_title="YCH_HR - Onboarding Platform", layout="wide")

st.sidebar.title("🏢 YCH_HR Workspace")
st.sidebar.caption("Logistics Roster Management Platform")
st.sidebar.markdown("---")

# ✅ FIXED RE-ORDERED SEQUENCE MAPPING: Arranged radio list precisely as requested
menu = st.sidebar.radio(
    "WORKSPACE MENU", 
    ["📊 New Hires Dashboard", "➕ Add New Employee", "📋 Task Checklist View", "🗃️ Archived Roster", "📤 Export Reports", "🚨 System Administration"]
)

# --- VIEW 1: ACTIVE DASHBOARD ---
if menu == "📊 New Hires Dashboard":
    st.title("Active Onboarding Dashboard")
    st.caption("High-level control room to track active candidates across all 5 operational milestones.")
    st.markdown("---")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM new_hires WHERE status = 'Active'")
    active_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM new_hires WHERE status = 'Archived'")
    archived_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT id FROM new_hires WHERE status = 'Active'")
    active_ids = cursor.fetchall()
    
    total_avg_pct = 0
    pending_count = 0
    active_hires_list = []
    
    for row in active_ids:
        h_id = row[0]
        overall, phase_breakdown, _, _ = calculate_completion_metrics(h_id)
        total_avg_pct += overall
        if overall < 100:
            pending_count += 1
            
        cursor.execute("SELECT employee_id, mobile_number, name, role, department, manager, start_date, gender FROM new_hires WHERE id = ?", (h_id,))
        w_info = cursor.fetchone()
        active_hires_list.append((h_id, w_info, overall, phase_breakdown))
        
    avg_completion = int(total_avg_pct / active_count) if active_count > 0 else 0
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Active Employees", active_count)
    kpi2.metric("Archived Employees", archived_count)
    kpi3.metric("Average Completion Rate", f"{avg_completion}%")
    kpi4.metric("Pending Employees", pending_count)
    st.markdown("---")
    
    if not active_hires_list:
        st.info("No active onboarding records found.")
    else:
        grid = st.columns(3)
        for idx, (h_id, details, overall_pct, phase_data) in enumerate(active_hires_list):
            emp_id, mobile, name, role, dept, manager, start_date, gender = details
            gender_icon = "👨" if gender == "Male" else "👩"
            
            with grid[idx % 3]:
                with st.container(border=True):
                    st.subheader(f"{gender_icon} {name}")
                    st.markdown(f"🆔 **Employee ID:** `{emp_id}` | 📱 **Mobile:** `{mobile}`")
                    st.markdown(f"🏢 **Department:** `{dept}`")
                    st.markdown(f"💼 **Position:** `{role}` | 👤 **Manager:** `{manager}`")
                    st.write(f"**Deployment Date:** {start_date}")
                    st.markdown("---")
                    
                    st.write(f"**Overall Progress Status:** `{overall_pct}%`")
                    st.progress(overall_pct / 100)
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        raw_channel_msg = generate_whatsapp_message(emp_id, name, dept, role, manager, start_date)
                        encoded_channel = urllib.parse.quote(raw_channel_msg)
                        GROUP_TOKEN = "JIeWsX45KJEAWsavJUZAff"
                        channel_url = f"https://api.whatsapp.com/send?phone=&text={encoded_channel}&context={GROUP_TOKEN}"
                        st.markdown(f'<a href="{channel_url}" target="_blank"><button style="background-color:#0078D4; color:white; border:none; padding:8px 12px; border-radius:4px; font-weight:bold; font-size:12px; cursor:pointer; width:100%;">📢 Channel Broadcast</button></a>', unsafe_allow_html=True)
                    
                    with btn_col2:
                        raw_progress_msg = (
                            f"📊 *YCH Onboarding Progress Update*\n\n"
                            f"• *Employee ID:* {emp_id}\n"
                            f"• *Name:* {name}\n"
                            f"📈 *Overall Completion:* {overall_pct}%\n"
                            f"• Phase 1: {phase_data['Phase 1']}%\n"
                            f"• Phase 2: {phase_data['Phase 2']}%\n"
                            f"• Phase 3: {phase_data['Phase 3']}%\n"
                            f"• Phase 4: {phase_data['Phase 4']}%\n"
                            f"• Phase 5: {phase_data['Phase 5']}%\n\n"
                            f"Please continue completing the remaining onboarding requirements."
                        )
                        clean_phone = re.sub(r'\D', '', mobile)
                        encoded_progress = urllib.parse.quote(raw_progress_msg)
                        employee_sms_url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_progress}"
                        st.markdown(f'<a href="{employee_sms_url}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:8px 12px; border-radius:4px; font-weight:bold; font-size:12px; cursor:pointer; width:100%;">📲 Send Progress Update</button></a>', unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if overall_pct == 100:
                        st.success("🎉 All Checklists Complete!")
                        if st.button(f"🗃️ Archive {name.split()[0]}", key=f"arch_btn_{h_id}", use_container_width=True):
                            cursor.execute("UPDATE new_hires SET status = 'Archived' WHERE id = ?", (h_id,))
                            conn.commit()
                            st.rerun()
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                    for phase in PHASE_GROUPS:
                        p_short = phase.split(":")[0]
                        p_rate = phase_data[p_short]
                        st.caption(f"**{p_short}:** {p_rate}%")
                        st.progress(p_rate / 100)
    conn.close()

# --- VIEW 2: EMPLOYEE REGISTRATION FORM ---
elif menu == "➕ Add New Employee":
    st.title("Employee Onboarding Profiles Engine")
    st.caption("Deploy standard operational tracks down to background ledger layers safely.")
    st.markdown("---")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT manager_name FROM managers ORDER BY manager_name ASC")
    manager_query = cursor.fetchall()
    manager_options = [row[0] for row in manager_query]
    conn.close()
    
    st.subheader("➕ Register New Candidate")
    with st.form("registration_form_master", clear_on_submit=False):
        input_emp_id = st.text_input("Employee ID Number:", placeholder="Example format requirement: SG0001").strip()
        input_name = st.text_input("Full Name:", placeholder="e.g. JAVIER BENEDICT CUEVILLAS")
        input_mobile = st.text_input("Mobile Number (Minimum 8 digits, numeric only):", placeholder="e.g. 81039323").strip()
        input_gender = st.selectbox("Gender Classification:", ["Male", "Female"])
        input_dept = st.selectbox("Allocated Corporate Account Department Hub:", YCH_DEPARTMENTS)
        input_role = st.text_input("Job Title / Position Role:", placeholder="e.g. Reach Truck Operator")
        input_manager = st.selectbox("Reporting Manager / PIC:", manager_options) if manager_options else "No Manager Assigned"
        input_date_picker = st.date_input("Start Training Deployment Date:")
        
        submit_button = st.form_submit_button("Deploy Onboarding Track & Format Alert")
        
        if submit_button:
            id_pattern = r"^[A-Z]{2}[0-9]{4}$"
            clean_mobile_check = re.sub(r'\D', '', input_mobile)
            
            if not re.match(id_pattern, input_emp_id):
                st.error("Employee ID must follow format: SG0001 (2 Capital Letters followed by exactly 4 numbers).")
            elif input_mobile == "" or len(clean_mobile_check) < 8 or clean_mobile_check != input_mobile:
                st.error("Mobile Number is required, must contain numbers only, and meet a minimum of 8 digits length.")
            elif input_name == "" or input_role == "" or input_manager == "No Manager Assigned":
                st.error("Please fill out Name, Role, and select an active Reporting Manager to build data blocks.")
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM new_hires WHERE UPPER(employee_id) = UPPER(?)", (input_emp_id,))
                duplicate = cursor.fetchone()
                
                if duplicate is not None:
                    st.error(f"🚨 DUPLICATE ID BLOCKED: That ID code is already registered to '{duplicate[0]}'.")
                    conn.close()
                else:
                    saved_date_string = input_date_picker.strftime("%B %d, %Y")
                    cursor.execute(
                        "INSERT INTO new_hires (employee_id, mobile_number, name, role, department, manager, start_date, gender, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active')",
                        (input_emp_id, input_mobile, input_name, input_role, input_dept, input_manager, saved_date_string, input_gender)
                    )
                    new_hire_id = cursor.lastrowid
                    
                    default_tasks = [
                        # Phase 1
                        ("Contract Signing", "Phase 1: Pre-boarding Checklist", "HR Team"),
                        ("Declaration Form Submission", "Phase 1: Pre-boarding Checklist", "HR Team"),
                        ("Familiarization Orientation Briefing", "Phase 1: Pre-boarding Checklist", "HR Team"),
                        ("Accountability Form Completion", "Phase 1: Pre-boarding Checklist", "HR Team"),
                        
                        # Phase 2
                        ("HR Onboarding Documentation Processing", "Phase 2: Day 1 Checklist", "HR Team"),
                        ("Security Training and Warehouse Entry Processing", "Phase 2: Day 1 Checklist", "Security Team"),
                        ("QA&EHS Training and Safety Protocol Review", "Phase 2: Day 1 Checklist", "QA&EHS Team"),
                        
                        # Phase 3
                        ("SOP Orientation Completed", "Phase 3: Technical Training Checklist", "Ops Team"),
                        ("Work Instruction Training Completed", "Phase 3: Technical Training Checklist", "Ops Team"),
                        ("Equipment Handling Training Completed", "Phase 3: Technical Training Checklist", "QA&EHS Team"),
                        ("Warehouse Operations Training Completed", "Phase 3: Technical Training Checklist", "Ops Team"),
                        ("Safety Procedures Training Completed", "Phase 3: Technical Training Checklist", "QA&EHS Team"),
                        ("System/Application Training Completed", "Phase 3: Technical Training Checklist", "Ops Team"),
                        ("Forklift Training Completed (If Applicable)", "Phase 3: Technical Training Checklist", "QA&EHS Team"),
                        ("On-the-Job Training Completed", "Phase 3: Technical Training Checklist", "Ops Team"),
                        ("Technical Competency Assessment Completed", "Phase 3: Technical Training Checklist", "QA&EHS Team"),
                        
                        # Phase 4
                        ("Employee understands job responsibilities", "Phase 4: Performance Assessment Checklist", "HR Team"),
                        ("Employee understands account operations", "Phase 4: Performance Assessment Checklist", "HR Team"),
                        ("Employee understands KPIs", "Phase 4: Performance Assessment Checklist", "HR Team"),
                        ("Employee can perform assigned tasks independently", "Phase 4: Performance Assessment Checklist", "QA&EHS Team"),
                        ("Employee demonstrates productivity expectations", "Phase 4: Performance Assessment Checklist", "HR Team"),
                        ("Employee follows SOP consistently", "Phase 4: Performance Assessment Checklist", "QA&EHS Team"),
                        ("Employee requires minimal supervision", "Phase 4: Performance Assessment Checklist", "HR Team"),
                        ("Employee has adapted to the work environment", "Phase 4: Performance Assessment Checklist", "HR Team"),
                        
                        # Phase 5
                        ("Employee introduced to operations team", "Phase 5: Employee Engagement & Follow-up Checklist", "HR Team"),
                        ("Employee introduced to workplace buddy", "Phase 5: Employee Engagement & Follow-up Checklist", "HR Team"),
                        ("PPE issuance completed", "Phase 5: Employee Engagement & Follow-up Checklist", "QA&EHS Team"),
                        ("Employee feedback session completed", "Phase 5: Employee Engagement & Follow-up Checklist", "HR Team"),
                        ("30-Day onboarding review completed", "Phase 5: Employee Engagement & Follow-up Checklist", "HR Team"),
                        ("Employee concerns addressed", "Phase 5: Employee Engagement & Follow-up Checklist", "HR Team"),
                        ("Manager follow-up completed", "Phase 5: Employee Engagement & Follow-up Checklist", "HR Team")
                    ]
                    
                    for t_name, p_name, own in default_tasks:
                        cursor.execute("INSERT INTO tasks (hire_id, task_name, phase, assigned_to, department) VALUES (?, ?, ?, ?, ?)", (new_hire_id, t_name, p_name, own, input_dept))
                        
                    conn.commit()
                    conn.close()
                    
                    channel_msg = generate_whatsapp_message(input_emp_id, input_name, input_dept, input_role, input_manager, saved_date_string)
                    st.session_state["last_registered_worker"] = {"name": input_name, "msg_text": channel_msg}
                    st.rerun()

    if "last_registered_worker" in st.session_state:
        w = st.session_state["last_registered_worker"]
        enc_msg = urllib.parse.quote(w["msg_text"])
        GROUP_TOKEN = "JIeWsX45KJEAWsavJUZAff"
        f_url = f"https://api.whatsapp.com/send?phone=&text={enc_msg}&context={GROUP_TOKEN}"
        
        st.markdown("---")
        st.success(f"🎉 Roster file profile successfully created for {w['name']}!")
        st.markdown(f'<a href="{f_url}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:14px 28px; border-radius:6px; font-weight:bold; font-size:16px; cursor:pointer; width:100%; box-shadow: 0px 4px 10px rgba(0,0,0,0.1);">🚀 Deploy Direct WhatsApp Group Notification</button></a>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Clear Notification & Register Next Profile"):
            del st.session_state["last_registered_worker"]
            st.rerun()

# --- VIEW 3: CHECKLIST RENDERING INTERFACE LAYER ---
elif menu == "📋 Task Checklist View":
    st.title("Operational Verification — Checklist Layer")
    st.caption("Manage granular structural checklist processing rows mapped by targeted phase constraints.")
    st.markdown("---")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, employee_id, name FROM new_hires WHERE status = 'Active'")
    employee_options = cursor.fetchall()
    
    if not employee_options:
        st.info("No active employee tracks currently available.")
    else:
        employee_dict = {f"[{emp_id}] {name}": h_id for h_id, emp_id, name in employee_options}
        selected_profile = st.selectbox("Select an employee to manage:", list(employee_dict.keys()))
        selected_id = employee_dict[selected_profile]
        
        left_col, right_col = st.columns([2, 1], gap="large")
        
        with left_col:
            for current_phase in PHASE_GROUPS:
                st.markdown(f"### 📋 {current_phase}")
                cursor.execute("SELECT id, task_name, assigned_to, is_completed FROM tasks WHERE hire_id = ? AND phase = ?", (selected_id, current_phase))
                tasks = cursor.fetchall()
                
                if not tasks:
                    st.caption("_No specific tasks added to this phase module._")
                else:
                    for t_id, task_name, assigned_to, is_completed in tasks:
                        t_space, b_space = st.columns([4, 1])
                        
                        with t_space:
                            checked = st.checkbox(
                                label=f"**{task_name}** (Assigned to: `{assigned_to}`)", 
                                value=bool(is_completed),
                                key=f"tsk_chk_{t_id}"
                            )
                            new_status = 1 if checked else 0
                            if new_status != is_completed:
                                cursor.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (new_status, t_id))
                                conn.commit()
                                st.rerun()
                                
                        with b_space:
                            if st.button("🗑️ Drop", key=f"drop_tsk_{t_id}", help="Remove this task if not applicable to this employee"):
                                cursor.execute("DELETE FROM tasks WHERE id = ?", (t_id,))
                                conn.commit()
                                st.success("Task dropped!")
                                st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)
                        
        with right_col:
            st.subheader("➕ Create Custom Task")
            with st.form("custom_task_form", clear_on_submit=True):
                new_task_name = st.text_input("Task Title Data:", placeholder="e.g. Process Site Badge Clearance")
                new_phase = st.selectbox("Assign to Roadmap Phase Location:", PHASE_GROUPS)
                new_owner = st.selectbox("Assign Owner Team Role:", AVAILABLE_TEAMS)
                
                if st.form_submit_button("Add Task to Active Checklist") and new_task_name != "":
                    cursor.execute("INSERT INTO tasks (hire_id, task_name, phase, assigned_to, department, is_completed) VALUES (?, ?, ?, ?, ?, 0)", (selected_id, new_task_name, new_phase, new_owner, new_owner))
                    conn.commit()
                    st.success("Custom task appended cleanly!")
                    st.rerun()
    conn.close()

# --- VIEW 4: ARCHIVED ROSTER ---
elif menu == "🗃️ Archived Roster":
    st.title("🗃️ Archived Onboarding Records")
    st.caption("Historically compiled read-only database logs of verified operational assets.")
    st.markdown("---")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, employee_id, mobile_number, name, role, department, manager, start_date, gender FROM new_hires WHERE status = 'Archived'")
    archived_hires = cursor.fetchall()
    
    if not archived_hires:
        st.info("No archived records found.")
    else:
        cols = st.columns(3)
        for idx, (h_id, emp_id, mobile, name, role, dept, manager, start_date, gender) in enumerate(archived_hires):
            gender_icon = "👨" if gender == "Male" else "👩"
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(f"{gender_icon} {name} (Archived)")
                    st.markdown(f"🆔 **Employee ID:** `{emp_id}` | 📱 **Mobile:** `{mobile}`")
                    st.markdown(f"🏢 **Department:** `{dept}`")
                    st.markdown(f"💼 **Position:** `{role}`")
                    st.write(f"**Reporting To:** {manager}")
                    st.markdown("---")
                    st.success("💯 100% Onboarding Verification Complete")
                    
                    if st.button("⏪ Restore to Active Dashboard", key=f"restore_btn_{h_id}", use_container_width=True):
                        cursor.execute("UPDATE new_hires SET status = 'Active' WHERE id = ?", (h_id,))
                        conn.commit()
                        st.rerun()
    conn.close()

# --- VIEW 5: EXPORT CENTER ---
elif menu == "📤 Export Reports":
    st.title("📤 Data Extraction & Excel Export Center")
    st.caption("Download structured corporate telemetry logs directly into local spreadsheets.")
    st.markdown("---")
    
    with st.container(border=True):
        st.subheader("📊 Choose Extraction Dataset Target")
        target_report = st.selectbox("Select Target Roster Context Scope:", ["Export Active Employees", "Export Archived Employees", "Export All Employees"])
        st.markdown("---")
        
        conn = get_db_connection()
        base_query = "SELECT id, employee_id, name, mobile_number, gender, department, role, manager, start_date, status FROM new_hires"
        if "Active" in target_report:
            base_query += " WHERE status = 'Active'"
            filename = "active_employees.xlsx"
        elif "Archived" in target_report:
            base_query += " WHERE status = 'Archived'"
            filename = "archived_employees.xlsx"
        else:
            filename = "all_employees.xlsx"
            
        df = pd.read_sql_query(base_query, conn)
        
        pct_array = []
        for _, row in df.iterrows():
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(is_completed) FROM tasks WHERE hire_id = ?", (int(row['id']),))
            t_t, t_c = cursor.fetchone()
            t_c = t_c if t_c else 0
            rate_string = f"{int((t_c / t_t) * 100)}%" if t_t > 0 else "0%"
            pct_array.append(rate_string)
            
        df['Overall Completion %'] = pct_array
        df = df.drop(columns=['id']).rename(columns={
            'employee_id': 'Employee ID', 'name': 'Full Name', 'mobile_number': 'Mobile Number',
            'gender': 'Gender', 'department': 'Department', 'role': 'Position',
            'manager': 'Reporting Manager', 'start_date': 'Start Date', 'status': 'Status'
        })
        conn.close()
        
        excel_stream = io.BytesIO()
        with pd.ExcelWriter(excel_stream, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='YCH_Roster_Audit')
            
        st.download_button(
            label=f"📥 Download Compiled Excel Sheet ({filename})",
            data=excel_stream.getvalue(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# --- VIEW 6: SYSTEM ADMINISTRATION ---
elif menu == "🚨 System Administration":
    st.title("System Records & Settings Administration")
    st.caption("Manage lookup constraints data lists, system dropdown values, and administrative purges.")
    st.markdown("---")
    
    admin_col1, admin_col2 = st.columns([1, 1], gap="large")
    
    with admin_col1:
        st.subheader("👤 Managers Masterlist Settings")
        with st.form("admin_manager_form", clear_on_submit=True):
            new_m_name = st.text_input("Enter New Operation Coordinator Name:")
            if st.form_submit_button("➕ Register Manager") and new_m_name != "":
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO managers (manager_name) VALUES (?)", (new_m_name.strip(),))
                    conn.commit()
                    st.success(f"Added '{new_m_name}' to validation lists successfully!")
                except sqlite3.IntegrityError:
                    st.error("This user object already exists inside system memory blocks.")
                conn.close()
                st.rerun()
                
        st.markdown("<br>", unsafe_allow_html=True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, manager_name FROM managers ORDER BY manager_name ASC")
        m_list = cursor.fetchall()
        conn.close()
        
        if m_list:
            with st.form("remove_manager_form_admin", clear_on_submit=True):
                m_dict = {m_name: m_id for m_id, m_name in m_list}
                target_m = st.selectbox("Select entries profile to clear out:", list(m_dict.keys()))
                if st.form_submit_button("❌ Remove Selected Manager", type="primary"):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM managers WHERE id = ?", (m_dict[target_m],))
                    conn.commit()
                    conn.close()
                    st.success("Target entry cleared out of options successfully.")
                    st.rerun()

    with admin_col2:
        st.subheader("🚨 Danger Zone: Purge Record Entry")
        st.caption("Permanently clear out an entry structure profile, wiping all historic checklist rows entirely.")
        st.markdown("<br>", unsafe_allow_html=True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, employee_id, name FROM new_hires")
        delete_options = cursor.fetchall()
        
        if not delete_options:
            st.info("No employee record profiles detected inside background tables.")
        else:
            delete_dict = {f"[{emp_id}] {name}": h_id for h_id, emp_id, name in delete_options}
            target_profile = st.selectbox("Select card to clear out completely:", list(delete_dict.keys()))
            target_id = delete_dict[target_profile]
            confirm_check = st.checkbox("I confirm that I want to permanently delete this worker.")
            if st.button("Permanently Erase Profile", type="primary") and confirm_check:
                cursor.execute("DELETE FROM tasks WHERE hire_id = ?", (target_id,))
                cursor.execute("DELETE FROM new_hires WHERE id = ?", (target_id,))
                conn.commit()
                st.success("Record elements completely cleared from all structural system layers.")
                st.rerun()
        conn.close()
