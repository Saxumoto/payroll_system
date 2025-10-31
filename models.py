import sqlite3
from flask_login import UserMixin
from werkzeug.security import generate_password_hash

# 🔧 Create both employee and user tables
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Create employees table
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            salary REAL NOT NULL,
            department TEXT,
            payroll_period TEXT,
            date TEXT,
            photo TEXT,
            hourly_rate REAL
        )
    ''')

    # Create users table (admin-only)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            status TEXT DEFAULT 'approved'
        )
    ''')

    # Create attendance table
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT,
            clock_in TEXT,
            clock_out TEXT,
            total_hours REAL,
            overtime_hours REAL DEFAULT 0,
            absences REAL DEFAULT 0,
            payroll_period TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    # Create deductions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS deductions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            loan REAL DEFAULT 0,
            payroll_period TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    conn.commit()
    conn.close()
# 👤 Flask-Login user model
class User(UserMixin):
    def __init__(self, id, username, password, role='admin', status='approved'):
        self.id = id
        self.username = username
        self.password = password
        self.role = role
        self.status = status

# 🔍 Get user by username
def get_user_by_username(username):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return User(*row)
    return None

# ➕ Add admin user
def add_user(username, password, role='admin'):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Check if user already exists
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    if c.fetchone():
        print(f"User '{username}' already exists.")
        conn.close()
        return

    # Hash and insert
    hashed_pw = generate_password_hash(password)
    c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, hashed_pw, role))
    conn.commit()
    conn.close()
    print(f"Admin user '{username}' created successfully.")

# ➕ Add employee
def add_employee(name, position, department, salary, payroll_period, date, photo, hourly_rate):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO employees (name, position, department, salary, payroll_period, date, photo, hourly_rate) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, position, department, salary, payroll_period, date, photo, hourly_rate))
    conn.commit()
    conn.close()

# 📋 Get all employees
def get_employees():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM employees')
    employees = c.fetchall()
    conn.close()
    return employees

# 🔍 Get employee by ID
def get_employee_by_id(emp_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM employees WHERE id = ?', (emp_id,))
    employee = c.fetchone()
    conn.close()
    return employee

# ✏️ Update employee
def update_employee(emp_id, name, position, department, salary, payroll_period, date, photo, hourly_rate):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        UPDATE employees 
        SET name = ?, position = ?, department = ?, salary = ?, payroll_period = ?, date = ?, photo = ?, hourly_rate = ?
        WHERE id = ?
    ''', (name, position, department, salary, payroll_period, date, photo, hourly_rate, emp_id))
    conn.commit()
    conn.close()

# ❌ Delete employee
def delete_employee(emp_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM employees WHERE id = ?', (emp_id,))
    conn.commit()
    conn.close()