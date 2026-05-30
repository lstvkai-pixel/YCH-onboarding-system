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

    # ✅ FIXED: Drop old table to allow new column structure to initialize correctly
    cursor.execute("DROP TABLE IF EXISTS user_accounts")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL DEFAULT 'YCH1234',
            role_type TEXT NOT NULL DEFAULT 'Employee',
            force_password_change INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO user_accounts (employee_id, password, role_type, force_password_change) VALUES ('HR0001', 'YCHADMIN', 'Employer', 0)")
    
    # ... (Keep the rest of your init_database code exactly as it was)
