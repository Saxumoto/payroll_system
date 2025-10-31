import sqlite3
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
    
    # Create employees table
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            department TEXT,
            salary REAL,
            payroll_period TEXT,
            date TEXT,
            photo TEXT,
            hourly_rate REAL
        )
    ''')
    
    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

# --- Employee Functions ---

def add_employee(name, position, department, salary, payroll_period, date, photo, hourly_rate):
    """Adds a new employee to the database."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO employees (name, position, department, salary, payroll_period, date, photo, hourly_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, position, department, salary, payroll_period, date, photo, hourly_rate))
    conn.commit()
    conn.close()

def get_employees():
    """Fetches all employees from the database."""
    conn = get_db_connection()
    # conn.row_factory = sqlite3.Row (This is now set in get_db_connection)
    c = conn.cursor()
    c.execute('SELECT * FROM employees ORDER BY name')
    employees = c.fetchall()
    conn.close()
    return employees

def get_employee_by_id(emp_id):
    """Fetches a single employee by their ID."""
    conn = get_db_connection()
    # conn.row_factory = sqlite3.Row (This is now set in get_db_connection)
    c = conn.cursor()
    c.execute('SELECT * FROM employees WHERE id = ?', (emp_id,))
    employee = c.fetchone()
    conn.close()
    return employee

def update_employee(emp_id, name, position, department, salary, payroll_period, date, photo, hourly_rate):
    """Updates an existing employee's information."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE employees 
        SET name = ?, position = ?, department = ?, salary = ?, 
            payroll_period = ?, date = ?, photo = ?, hourly_rate = ?
        WHERE id = ?
    ''', (name, position, department, salary, payroll_period, date, photo, hourly_rate, emp_id))
    conn.commit()
    conn.close()

def delete_employee(emp_id):
    """Deletes an employee from the database by ID."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM employees WHERE id = ?', (emp_id,))
    conn.commit()
    conn.close()

# --- User Functions ---

def create_user(username, password_hash, is_admin=0):
    """Creates a new user."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO users (username, password_hash, is_admin) 
        VALUES (?, ?, ?)
    ''', (username, password_hash, is_admin))
    conn.commit()
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

# Example of how to add an admin user (run this manually if needed)
def make_user_admin(username):
    """Updates a user to be an admin."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET is_admin = 1 WHERE username = ?', (username,))
    conn.commit()
    conn.close()
    print(f"User {username} is now an admin.")

if __name__ == '__main__':
    # This initializes the database when models.py is run directly
    init_db()
    print("Database initialized.")
