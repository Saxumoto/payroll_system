import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'database.db'

def get_db_connection():
    """Creates a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This is key for accessing columns by name
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # --- UPDATED: employees table ---
    # Added fields for contact, statutory numbers, and employment status
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            department TEXT,
            salary REAL,
            payroll_period TEXT,
            date_hired TEXT,
            photo TEXT,
            hourly_rate REAL,

            -- New fields for Employee Records
            contact_number TEXT,
            address TEXT,
            bank_account_number TEXT,
            
            -- New fields for Deductions
            sss_number TEXT,
            philhealth_number TEXT,
            pagibig_number TEXT,
            tin_number TEXT,
            
            -- New fields for Employment History
            date_resigned TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # --- UPDATED: users table ---
    # Added employee_id to link a user account to an employee profile
    # This allows an employee to log in and view their *own* data.
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            employee_id INTEGER,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')
    
    # --- NEW: time_records table ---
    # For Time and Attendance Management
    c.execute('''
        CREATE TABLE IF NOT EXISTS time_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            hours_worked REAL DEFAULT 0.0,
            overtime_hours REAL DEFAULT 0.0,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    # --- NEW: leave_requests table ---
    # For Leave Management
    c.execute('''
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            leave_type TEXT NOT NULL, -- e.g., 'Vacation', 'Sick'
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending', -- 'Pending', 'Approved', 'Rejected'
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    # --- NEW: loans table ---
    # For company loans and other deductions
    c.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            loan_name TEXT DEFAULT 'Company Loan',
            total_amount REAL NOT NULL,
            amount_paid REAL DEFAULT 0.0,
            monthly_deduction REAL NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    # --- NEW: payslips table ---
    # For storing historical payslips
    c.execute('''
        CREATE TABLE IF NOT EXISTS payslips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            pay_period_start TEXT NOT NULL,
            pay_period_end TEXT NOT NULL,
            gross_pay REAL,
            overtime_pay REAL,
            allowances REAL,
            sss_deduction REAL,
            philhealth_deduction REAL,
            pagibig_deduction REAL,
            tax_deduction REAL,
            loan_deductions REAL,
            total_deductions REAL,
            net_pay REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# --- Employee Functions (Updated) ---

def add_employee(name, position, department, salary, payroll_period, date_hired, photo, hourly_rate,
                 contact_number, address, bank_account_number, 
                 sss_number, philhealth_number, pagibig_number, tin_number):
    """Adds a new employee to the database."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO employees (
            name, position, department, salary, payroll_period, date_hired, photo, hourly_rate,
            contact_number, address, bank_account_number, sss_number, philhealth_number, pagibig_number, tin_number
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, position, department, salary, payroll_period, date_hired, photo, hourly_rate,
          contact_number, address, bank_account_number, sss_number, philhealth_number, pagibig_number, tin_number))
    conn.commit()
    conn.close()

def get_employees():
    """Fetches all *active* employees from the database."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM employees WHERE is_active = 1 ORDER BY name')
    employees = c.fetchall()
    conn.close()
    return employees

def get_all_employees():
    """Fetches *all* employees from the database, including inactive."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM employees ORDER BY name')
    employees = c.fetchall()
    conn.close()
    return employees

def get_employee_by_id(emp_id):
    """Fetches a single employee by their ID."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM employees WHERE id = ?', (emp_id,))
    employee = c.fetchone()
    conn.close()
    return employee

def update_employee(emp_id, name, position, department, salary, payroll_period, date_hired, photo, hourly_rate,
                    contact_number, address, bank_account_number, 
                    sss_number, philhealth_number, pagibig_number, tin_number):
    """Updates an existing employee's information."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE employees 
        SET name = ?, position = ?, department = ?, salary = ?, 
            payroll_period = ?, date_hired = ?, photo = ?, hourly_rate = ?,
            contact_number = ?, address = ?, bank_account_number = ?,
            sss_number = ?, philhealth_number = ?, pagibig_number = ?, tin_number = ?
        WHERE id = ?
    ''', (name, position, department, salary, payroll_period, date_hired, photo, hourly_rate,
          contact_number, address, bank_account_number, sss_number, philhealth_number, pagibig_number, tin_number,
          emp_id))
    conn.commit()
    conn.close()

def archive_employee(emp_id, resignation_date=None):
    """
    Archives an employee (sets is_active=0) instead of deleting.
    This preserves their record for history.
    """
    if not resignation_date:
        resignation_date = datetime.date.today().isoformat()
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE employees SET is_active = 0, date_resigned = ? WHERE id = ?', (resignation_date, emp_id))
    conn.commit()
    conn.close()

# --- User Functions (Updated) ---

def create_user(username, password, is_admin=0, employee_id=None):
    """Creates a new user with a hashed password."""
    password_hash = generate_password_hash(password)
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO users (username, password_hash, is_admin, employee_id) 
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, is_admin, employee_id))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Error: Username '{username}' already exists.")
    finally:
        conn.close()

def get_user_by_username(username):
    """Fetches a user by their username."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    """Fetches a user by their ID."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_all_users():
    """Fetches all users from the database."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users ORDER BY username')
    users = c.fetchall()
    conn.close()
    return users

def update_user_links(user_id, employee_id, is_admin):
    """Updates a user's employee link and admin status."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET employee_id = ?, is_admin = ?
        WHERE id = ?
    ''', (employee_id, is_admin, user_id))
    conn.commit()
    conn.close()

def make_user_admin(username):
    """Updates a user to be an admin."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET is_admin = 1 WHERE username = ?', (username,))
    conn.commit()
    conn.close()
    print(f"User {username} is now an admin.")

# --- NEW Functions for other modules ---

# --- Time & Attendance Functions ---
def add_time_record(employee_id, date, hours_worked, overtime_hours):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO time_records (employee_id, date, hours_worked, overtime_hours)
        VALUES (?, ?, ?, ?)
    ''', (employee_id, date, hours_worked, overtime_hours))
    conn.commit()
    conn.close()

def get_time_records(employee_id, start_date, end_date):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM time_records 
        WHERE employee_id = ? AND date BETWEEN ? AND ?
        ORDER BY date
    ''', (employee_id, start_date, end_date))
    records = c.fetchall()
    conn.close()
    return records

# --- Loan Functions ---
def add_loan(employee_id, loan_name, total_amount, monthly_deduction):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO loans (employee_id, loan_name, total_amount, monthly_deduction)
        VALUES (?, ?, ?, ?)
    ''', (employee_id, loan_name, total_amount, monthly_deduction))
    conn.commit()
    conn.close()

def get_active_loans(employee_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM loans WHERE employee_id = ? AND is_active = 1', (employee_id,))
    loans = c.fetchall()
    conn.close()
    return loans

def update_loan_payment(loan_id, payment_amount):
    """Updates the amount paid on a loan and deactivates if fully paid."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT total_amount, amount_paid FROM loans WHERE id = ?', (loan_id,))
    loan = c.fetchone()
    
    if loan:
        new_amount_paid = loan['amount_paid'] + payment_amount
        is_active = 1
        if new_amount_paid >= loan['total_amount']:
            is_active = 0
            new_amount_paid = loan['total_amount'] # Don't overpay
            
        c.execute('''
            UPDATE loans 
            SET amount_paid = ?, is_active = ?
            WHERE id = ?
        ''', (new_amount_paid, is_active, loan_id))
        conn.commit()
    conn.close()

# --- Leave Functions ---
def add_leave_request(employee_id, leave_type, start_date, end_date, reason):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, reason)
        VALUES (?, ?, ?, ?, ?)
    ''', (employee_id, leave_type, start_date, end_date, reason))
    conn.commit()
    conn.close()

def get_leave_requests(employee_id=None, status='Pending'):
    conn = get_db_connection()
    c = conn.cursor()
    if employee_id:
        c.execute('SELECT * FROM leave_requests WHERE employee_id = ? AND status = ?', (employee_id, status))
    else:
        c.execute('SELECT * FROM leave_requests WHERE status = ?', (status,))
    requests = c.fetchall()
    conn.close()
    return requests

def update_leave_status(leave_id, status):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE leave_requests SET status = ? WHERE id = ?', (status, leave_id))
    conn.commit()
    conn.close()

# --- Payslip Functions ---
def create_payslip(employee_id, period_start, period_end, pay_details):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO payslips (
            employee_id, pay_period_start, pay_period_end,
            gross_pay, overtime_pay, allowances,
            sss_deduction, philhealth_deduction, pagibig_deduction,
            tax_deduction, loan_deductions, total_deductions, net_pay
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        employee_id, period_start, period_end,
        pay_details.get('gross_pay'), pay_details.get('overtime_pay'), pay_details.get('allowances'),
        pay_details.get('sss'), pay_details.get('philhealth'), pay_details.get('pagibig'),
        pay_details.get('tax'), pay_details.get('loans'), pay_details.get('total_deductions'),
        pay_details.get('net_pay')
    ))
    conn.commit()
    conn.close()

def get_payslips_by_employee(employee_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM payslips WHERE employee_id = ? ORDER BY pay_period_end DESC', (employee_id,))
    payslips = c.fetchall()
    conn.close()
    return payslips


if __name__ == '__main__':
    # This initializes the database when models.py is run directly
    print("Initializing database...")
    init_db()
    print("Database initialized with new schema.")
    
    # You can also add a default admin user here if you want
    try:
        print("Creating default admin user...")
        create_user('admin', 'admin', is_admin=1)
        print("Default admin user 'admin' with password 'admin' created.")
    except Exception as e:
        print(f"Could not create admin user (it might already exist): {e}")