import sqlite3
import streamlit as st
import urllib.parse

# ==========================================
# DATABASE BACKEND LOGIC (The Engine)
# ==========================================
def get_db_connection():
    return sqlite3.connect("onboarding.db")

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. New Hires Table (With Status column added for archiving)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS new_hires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL DEFAULT 'N/A',
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL DEFAULT 'HR Team',
            manager TEXT NOT NULL,
            start_date TEXT NOT NULL,
            gender TEXT NOT NULL DEFAULT 'Male',
            status TEXT NOT NULL DEFAULT 'Active'
        )
    ''')
    
    # Migration safety net: Adds 'status' column dynamically if it doesn't exist
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

def generate_whatsapp_message(emp_id, name, gender, dept, role, manager, start_date):
    return (
        f"🚨 *[YCH_HR Alert] New Onboarding Training Scheduled*\n\n"
        f"Dear Teams, a new employee profile has been deployed to the system roster. "
        f"Please prepare to conduct the required phased training sessions on their starting date:\n\n"
        f"📝 *EMPLOYEE LOGISTICS PROFILE:*\n"
        f"• *Employee ID:* {emp_id}\n"
        f"• *Full Name:* {name}\n"
        f"• *Gender:* {gender}\n"
        f"• *Account Department:* {dept}\n"
        f"• *Job Position:* {role}\n"
        f"• *Reporting Manager:* {manager}\n"
        f"• *Training Start Date:* {start_date}\n\n"
        f"Please monitor progress for Group 1, Group 2, and Group 3 checklists directly inside the system dashboard."
    )

# ==========================================
# STREAMLIT FRONTEND LOGIC (The Presentation)
# ==========================================
st.set_page_config(page_title="YCH_HR - Onboarding System", layout="wide")

st.sidebar.title("🏢 YCH_HR")
st.sidebar.caption("HR Onboarding Management System")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "WORKSPACE MENU", 
    ["📊 New Hires Dashboard", "🗃️ Archived Roster", "📋 Task Checklist View", "➕ Add New Employee", "🚨 System Administration"]
)

YCH_DEPARTMENTS = [
    "HR Department", "QAEHS Department", "Procurement Department",
    "Freight & Transport Department", "Finance Department", "Ops Abott_Inplant",
    "Ops Symrise Flavours SG", "Ops Symrise", "Ops Starbucks", "Ops HAP",
    "Ops LKK", "Ops 3M_Tech", "Ops 3M_Odessy", "Ops Philip_PH", "Ops Philip_HS"
]

AVAILABLE_TEAMS = ["HR Team", "Security Team", "QA&EHS Team"]
PHASE_GROUPS = [
    "Group 1: Pre-boarding Checklist", 
    "Group 2: Day 1 Checklist", 
    "Group 3: Monthly Engagement Checklist"
]

# --- VIEW 1: ACTIVE DASHBOARD ---
if menu == "📊 New Hires Dashboard":
    st.title("Active New Hires Dashboard")
    st.caption("Monitor active onboarding cases split by phase groups.")
    st.markdown("---")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    # Only pull Active profiles
    cursor.execute("SELECT id, employee_id, name, role, department, manager, start_date, gender FROM new_hires WHERE status = 'Active'")
    hires = cursor.fetchall()
    
    if not hires:
        st.info("No active onboarding profiles found.")
    else:
        cols = st.columns(3)
        for idx, (h_id, emp_id, name, role, dept, manager, start_date, gender) in enumerate(hires):
            gender_icon = "👨" if gender == "Male" else "👩"
            
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(f"{gender_icon} {name}")
                    st.markdown(f"🆔 **Employee ID:** `{emp_id}`")
                    st.markdown(f"🏢 **Department:** `{dept}`")
                    st.markdown(f"💼 **Position:** {role}")
                    st.write(f"**Reporting To:** {manager}")
                    st.write(f"**Expected Start:** {start_date}")
                    st.markdown("---")
                    
                    # WhatsApp Alert Button
                    raw_msg = generate_whatsapp_message(emp_id, name, gender, dept, role, manager, start_date)
                    encoded_msg = urllib.parse.quote(raw_msg)
                    GROUP_TOKEN = "JIeWsX45KJEAWsavJUZAff"
                    card_whatsapp_url = f"https://api.whatsapp.com/send?phone=&text={encoded_msg}&context={GROUP_TOKEN}"
                    
                    st.markdown(
                        f'<a href="{card_whatsapp_url}" target="_blank" style="text-decoration:none;">'
                        f'<button style="background-color:#25D366; color:white; border:none; padding:6px 12px; '
                        f'border-radius:4px; font-weight:bold; font-size:13px; cursor:pointer; width:100%; margin-bottom:12px;">'
                        f'💬 Broadcast Alert to WhatsApp Group'
                        f'</button></a>',
                        unsafe_allow_html=True
                    )
                    
                    # Calculate overall completion for archiving trigger
                    cursor.execute("SELECT COUNT(*), SUM(is_completed) FROM tasks WHERE hire_id = ?", (h_id,))
                    t_tot, t_comp = cursor.fetchone()
                    t_comp = t_comp if t_comp else 0
                    overall_pct = int((t_comp / t_tot) * 100) if t_tot > 0 else 0
                    
                    # If employee hits 100%, show a success banner and an Archive button
                    if overall_pct == 100:
                        st.success("🎉 All Checklists Complete!")
                        if st.button(f"🗃️ Archive {name.split()[0]}", key=f"arch_{h_id}"):
                            cursor.execute("UPDATE new_hires SET status = 'Archived' WHERE id = ?", (h_id,))
                            conn.commit()
                            st.rerun()
                        st.markdown("---")
                    
                    for current_phase in PHASE_GROUPS:
                        cursor.execute("SELECT COUNT(*), SUM(is_completed) FROM tasks WHERE hire_id = ? AND phase = ?", (h_id, current_phase))
                        total, completed = cursor.fetchone()
                        completed = completed if completed else 0
                        progress = int((completed / total) * 100) if total > 0 else 0
                        short_phase_name = current_phase.split(":")[0] 
                        
                        st.caption(f"**{short_phase_name} Progress:** {progress}%")
                        st.progress(progress / 100)
    conn.close()

# --- NEW VIEW 2: ARCHIVED ROSTER ---
elif menu == "🗃️ Archived Roster":
    st.title("🗃️ Archived Employee Records")
    st.caption("A read-only repository of successfully completed onboarding histories.")
    st.markdown("---")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    # Pull only Archived profiles
    cursor.execute("SELECT id, employee_id, name, role, department, manager, start_date, gender FROM new_hires WHERE status = 'Archived'")
    archived_hires = cursor.fetchall()
    
    if not archived_hires:
        st.info("No archived records found.")
    else:
        cols = st.columns(3)
        for idx, (h_id, emp_id, name, role, dept, manager, start_date, gender) in enumerate(archived_hires):
            gender_icon = "👨" if gender == "Male" else "👩"
            
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(f"{gender_icon} {name} (Archived)")
                    st.markdown(f"🆔 **Employee ID:** `{emp_id}`")
                    st.markdown(f"🏢 **Department:** `{dept}`")
                    st.markdown(f"💼 **Position:** {role}")
                    st.write(f"**Reporting To:** {manager}")
                    st.write(f"**Completed Roster Track:** {start_date}")
                    st.markdown("---")
                    st.success("💯 100% Onboarding Verification Complete")
                    
                    # Quick option to un-archive back to active dashboard if needed
                    if st.button("⏪ Restore to Active", key=f"rest_{h_id}"):
                        cursor.execute("UPDATE new_hires SET status = 'Active' WHERE id = ?", (h_id,))
                        conn.commit()
                        st.rerun()
    conn.close()

# --- VIEW 3: OPERATIONAL CHECKLIST LAYER ---
elif menu == "📋 Task Checklist View":
    st.title("Onboarding Assistant — Checklist Layer")
    st.markdown("---")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    # Checklists can only be managed for Active hires
    cursor.execute("SELECT id, employee_id, name FROM new_hires WHERE status = 'Active'")
    employee_options = cursor.fetchall()
    
    if not employee_options:
        st.info("No active employees registered yet.")
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
                    st.caption("_No specific tasks added._")
                else:
                    for t_id, task_name, assigned_to, is_completed in tasks:
                        checked = st.checkbox(label=f"**{task_name}** (Assigned to: `{assigned_to}`)", value=bool(is_completed), key=f"task_{t_id}")
                        new_status = 1 if checked else 0
                        if new_status != is_completed:
                            cursor.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (new_status, t_id))
                            conn.commit()
                            st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)
                        
        with right_col:
            st.subheader("➕ Create Custom Task")
            with st.form("new_task_form", clear_on_submit=True):
                new_task_name = st.text_input("Task Title:")
                new_phase = st.selectbox("Assign to Group Phase:", PHASE_GROUPS)
                new_owner = st.selectbox("Assign Owner Role:", AVAILABLE_TEAMS)
                
                add_task_btn = st.form_submit_button("Add Task to Checklist")
                if add_task_btn and new_task_name != "":
                    cursor.execute("INSERT INTO tasks (hire_id, task_name, phase, assigned_to, department, is_completed) VALUES (?, ?, ?, ?, ?, 0)", (selected_id, new_task_name, new_phase, new_owner, new_owner))
                    conn.commit()
                    st.success("Added custom task!")
                    st.rerun()
    conn.close()

# --- VIEW 4: EMPLOYEE REGISTRATION FORM ---
elif menu == "➕ Add New Employee":
    st.title("YCH Employee Profiles Management")
    st.markdown("---")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT manager_name FROM managers ORDER BY manager_name ASC")
    manager_query = cursor.fetchall()
    manager_options = [row[0] for row in manager_query]
    conn.close()
    
    st.subheader("➕ Register New Employee")
    with st.form("registration_form", clear_on_submit=False):
        input_emp_id = st.text_input("Employee ID Number:", placeholder="e.g. SG0001").strip()
        input_name = st.text_input("Full Name:", placeholder="e.g. JAVIER BENEDICT CUEVILLAS")
        input_gender = st.selectbox("Gender:", ["Male", "Female"])
        input_dept = st.selectbox("Allocated Department:", YCH_DEPARTMENTS)
        input_role = st.text_input("Job Title / Position:", placeholder="e.g. Forklift Operator")
        
        if not manager_options:
            st.warning("⚠️ No managers found in masterlist! Please add a manager in System Administration first.")
            input_manager = "No Manager Assigned"
        else:
            input_manager = st.selectbox("Reporting Manager / PIC:", manager_options)
            
        input_date_picker = st.date_input("Start Date:")
        submit_button = st.form_submit_button("Deploy Onboarding Track & Format Alert")
        
        if submit_button:
            if input_emp_id == "" or input_name == "" or input_role == "" or input_manager == "No Manager Assigned":
                st.error("Please fill out Employee ID, Name, Role, and select a Manager before saving.")
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM new_hires WHERE UPPER(employee_id) = UPPER(?)", (input_emp_id,))
                duplicate_record = cursor.fetchone()
                
                if duplicate_record is not None:
                    st.error(f"🚨 DUPLICATE ID DETECTED: The Employee ID '{input_emp_id}' is already assigned to '{duplicate_record[0]}'. Please provide a unique ID number.")
                    conn.close()
                else:
                    saved_date_string = input_date_picker.strftime("%B %d, %Y")
                    cursor.execute(
                        "INSERT INTO new_hires (employee_id, name, role, department, manager, start_date, gender, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')",
                        (input_emp_id, input_name, input_role, input_dept, input_manager, saved_date_string, input_gender)
                    )
                    new_hire_id = cursor.lastrowid
                    
                    default_roadmap_tasks = [
                        ("Contract signing", "Group 1: Pre-boarding Checklist", "HR Team"),
                        ("Declaration form submission", "Group 1: Pre-boarding Checklist", "HR Team"),
                        ("Familiarization orientation briefing", "Group 1: Pre-boarding Checklist", "HR Team"),
                        ("Accountability form completion", "Group 1: Pre-boarding Checklist", "HR Team"),
                        ("HR Onboarding documentation processing", "Group 2: Day 1 Checklist", "HR Team"),
                        ("Security Training and warehouse entry processing", "Group 2: Day 1 Checklist", "Security Team"),
                        ("QAEHS Training and safety protocols review", "Group 2: Day 1 Checklist", "QA&EHS Team"),
                        ("Has the specific standard operating procedure (SOP) of the assigned department/account been explained thoroughly?", "Group 3: Monthly Engagement Checklist", "HR Team"),
                        ("Has the employee been properly introduced to the operations team and workspace buddy?", "Group 3: Monthly Engagement Checklist", "HR Team"),
                        ("Is the employee comfortable operating specialized equipment/tools assigned to their account?", "Group 3: Monthly Engagement Checklist", "QA&EHS Team"),
                        ("Does the employee have all necessary Personal Protective Equipment (PPE) required for their daily account tasks?", "Group 3: Monthly Engagement Checklist", "QA&EHS Team"),
                        ("Follow-up session: Review feedback regarding their first 30 days and answer any operations questions.", "Group 3: Monthly Engagement Checklist", "HR Team")
                    ]
                    
                    for task_name, phase, assigned_to in default_roadmap_tasks:
                        cursor.execute("INSERT INTO tasks (hire_id, task_name, phase, assigned_to, department) VALUES (?, ?, ?, ?, ?)", (new_hire_id, task_name, phase, assigned_to, input_dept))
                    conn.commit()
                    conn.close()
                    
                    automated_msg = generate_whatsapp_message(input_emp_id, input_name, input_gender, input_dept, input_role, input_manager, saved_date_string)
                    st.session_state["last_registered_worker"] = {"name": input_name, "msg_text": automated_msg}
                    st.rerun()

    if "last_registered_worker" in st.session_state:
        w = st.session_state["last_registered_worker"]
        encoded_message = urllib.parse.quote(w["msg_text"])
        GROUP_TOKEN = "JIeWsX45KJEAWsavJUZAff"
        fixed_whatsapp_url = f"https://api.whatsapp.com/send?phone=&text={encoded_message}&context={GROUP_TOKEN}"
        
        st.markdown("---")
        st.success(f"🎉 Profile successfully saved for {w['name']}!")
        st.markdown(f'<a href="{fixed_whatsapp_url}" target="_blank" style="text-decoration:none;"><button style="background-color:#25D366; color:white; border:none; padding:14px 28px; border-radius:6px; font-weight:bold; font-size:16px; cursor:pointer; width:100%; box-shadow: 0px 4px 10px rgba(0,0,0,0.1);">🚀 Deploy Direct WhatsApp Group Notification</button></a>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Clear View & Register Next Record"):
            del st.session_state["last_registered_worker"]
            st.rerun()

# --- VIEW 5: SYSTEM ADMINISTRATION ---
elif menu == "🚨 System Administration":
    st.title("System Records & Settings Administration")
    st.markdown("---")
    admin_col1, admin_col2 = st.columns([1, 1], gap="large")
    
    with admin_col1:
        st.subheader("👤 Managers Masterlist Management")
        with st.form("add_manager_form", clear_on_submit=True):
            new_m_name = st.text_input("Enter New Manager Name:")
            submit_m = st.form_submit_button("➕ Register Manager")
            if submit_m and new_m_name != "":
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO managers (manager_name) VALUES (?)", (new_m_name.strip(),))
                    conn.commit()
                    st.success(f"Added '{new_m_name}' successfully!")
                except sqlite3.IntegrityError:
                    st.error("This manager is already registered.")
                conn.close()
                st.rerun()
                
        st.markdown("<br>", unsafe_allow_html=True)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, manager_name FROM managers ORDER BY manager_name ASC")
        m_list = cursor.fetchall()
        conn.close()
        
        if m_list:
            with st.form("remove_manager_form", clear_on_submit=True):
                m_dict = {m_name: m_id for m_id, m_name in m_list}
                target_m = st.selectbox("Select manager to remove:", list(m_dict.keys()))
                if st.form_submit_button("❌ Remove Selected Manager", type="primary"):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM managers WHERE id = ?", (m_dict[target_m],))
                    conn.commit()
                    conn.close()
                    st.rerun()

    with admin_col2:
        st.subheader("🚨 Danger Zone: Remove Employee Profile")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, employee_id, name FROM new_hires")
        delete_options = cursor.fetchall()
        
        if not delete_options:
            st.info("No records available to delete.")
        else:
            delete_dict = {f"[{emp_id}] {name}": h_id for h_id, emp_id, name in delete_options}
            target_profile = st.selectbox("Select profile to destroy permanently:", list(delete_dict.keys()))
            target_id = delete_dict[target_profile]
            confirm_check = st.checkbox("I confirm that I want to permanently delete this worker.")
            if st.button("Permanently Erase Profile", type="primary") and confirm_check:
                cursor.execute("DELETE FROM tasks WHERE hire_id = ?", (target_id,))
                cursor.execute("DELETE FROM new_hires WHERE id = ?", (target_id,))
                conn.commit()
                st.rerun()
        conn.close()
