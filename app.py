import os
import sqlite3
import uuid
import csv
import io
from flask import Flask, render_template, request, redirect, session, flash, url_for, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

# Import database functions from models.py
from models import (
    init_db,
    add_employee,
    get_employees,
    get_employee_by_id,
    update_employee,
    delete_employee,
    get_user_by_username,
    create_user
)

# Import utility functions from utils.py
from utils import (
    get_current_date,
    calculate_salary  # <-- Import the centralized calculator
)

# Import PDF generation service
from services.pdf_generator import generate_payroll_pdf

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_goes_here'  # Change this to a random secret key
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# User model for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password_hash, is_admin=0):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def get_is_admin(self):
        return self.is_admin

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_row = c.fetchone()
    conn.close()
    if user_row:
        return User(user_row['id'], user_row['username'], user_row['password_hash'], user_row['is_admin'])
    return None

# Custom decorator for admin-only routes
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.get_is_admin():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_row = get_user_by_username(username)
        
        if user_row and check_password_hash(user_row['password_hash'], password):
            user = User(user_row['id'], user_row['username'], user_row['password_hash'], user_row['is_admin'])
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        # Check if user already exists
        if get_user_by_username(username):
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        
        # Removed 'email' from the create_user call to match the database
        create_user(username, hashed_password)
        
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# 🔐 Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# --- Core Application Routes ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/employees')
@login_required
def employee_list():
    # Fetch employee data using the model function
    employees = get_employees()

    # Backend calculations
    total_employees = len(employees)
    total_salary = 0
    total_sss = 0
    total_philhealth = 0
    total_pagibig = 0
    net_total = 0

    employee_data_list = []

    for emp in employees:
        # Use the centralized calculator
        calcs = calculate_salary(emp['salary'])
        
        # Aggregate totals
        total_salary += calcs['salary']
        total_sss += calcs['sss']
        total_philhealth += calcs['philhealth']
        total_pagibig += calcs['pagibig']
        net_total += calcs['net_salary']
        
        # Append all data for the template
        emp_dict = dict(emp)  # Convert sqlite3.Row to dict
        emp_dict.update(calcs) # Add calculated values
        employee_data_list.append(emp_dict)

    # NOTE: This route correctly renders 'employees.html', which is the
    # template that works. 'employee_list.html' has a typo and is not used.
    return render_template('employees.html',
                           employees=employee_data_list,
                           total_employees=total_employees,
                           total_salary=f'{total_salary:,.2f}',
                           total_sss=f'{total_sss:,.2f}',
                           total_philhealth=f'{total_philhealth:,.2f}',
                           total_pagibig=f'{total_pagibig:,.2f}',
                           net_total=f'{net_total:,.2f}')

# ➕ Add new employee
@app.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required  # Only admins can add employees
def add_employee_route():
    if request.method == 'POST':
        name = request.form['name']
        position = request.form['position']
        department = request.form['department']
        salary = float(request.form['salary'])
        payroll_period = request.form['payroll_period'].strip().title()
        date = request.form['date'] or get_current_date()
        hourly_rate = request.form.get('hourly_rate', type=float)
        
        photo_filename = None
        photo_file = request.files.get('photo')

        if photo_file and photo_file.filename:
            # Generate a unique filename
            extension = os.path.splitext(secure_filename(photo_file.filename))[1]
            photo_filename = str(uuid.uuid4()) + extension
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            photo_file.save(photo_path)

        # Save to database using the model function
        add_employee(name, position, department, salary, payroll_period, date, photo_filename, hourly_rate)

        flash(f'Employee {name} added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_employee.html', current_date=get_current_date())

# ✏️ Edit employee
@app.route('/edit/<int:employee_id>', methods=['GET', 'POST'])
@login_required
@admin_required  # Only admins can edit employees
def edit_employee(employee_id):
    # Use the model function to get the employee
    employee = get_employee_by_id(employee_id)

    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        position = request.form['position']
        department = request.form['department']
        salary = float(request.form['salary'])
        payroll_period = request.form['payroll_period'].strip().title()
        date = request.form.get('date') or employee['date']
        hourly_rate = request.form.get('hourly_rate', type=float)

        # Handle photo upload
        photo_file = request.files.get('photo')
        photo_filename = employee['photo']  # default to existing

        if photo_file and photo_file.filename:
            # Generate a new unique filename
            extension = os.path.splitext(secure_filename(photo_file.filename))[1]
            photo_filename = str(uuid.uuid4()) + extension
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            photo_file.save(photo_path)
            
            # TODO: Delete the old photo if it's different
            # if employee['photo'] and employee['photo'] != photo_filename:
            #     old_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], employee['photo'])
            #     if os.path.exists(old_photo_path):
            #         os.remove(old_photo_path)

        # Use the model function to update
        update_employee(
            employee_id, name, position, department, salary, 
            payroll_period, date, photo_filename, hourly_rate
        )

        flash("Employee updated successfully.", "success")
        return redirect(url_for('dashboard'))

    return render_template('edit_employee.html', employee=employee)


# 🗑️ Delete employee
@app.route('/delete/<int:emp_id>', methods=['POST'])
@login_required
@admin_required  # Only admins can delete employees
def delete_employee_route(emp_id):
    try:
        # Fetch employee record to get photo filename
        employee = get_employee_by_id(emp_id)
        
        if employee and employee['photo']:
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], employee['photo'])
            if os.path.exists(photo_path):
                os.remove(photo_path)  # Delete the photo file

        # Use model function to delete from database
        delete_employee(emp_id)
        
        flash('Employee deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting employee: {e}', 'danger')
        
    return redirect(url_for('dashboard'))

# 🧾 View single employee payroll
@app.route('/payroll/<int:emp_id>')
@login_required
def view_payroll(emp_id):
    # Fetch employee record
    employee = get_employee_by_id(emp_id)

    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for('dashboard'))
    
    # Calculate deductions using the centralized calculator
    calcs = calculate_salary(employee['salary'])

    # Prepare details dictionary
    salary_details = {
        'id': employee['id'],
        'name': employee['name'],
        'position': employee['position'],
        'department': employee['department'],
        'payroll_period': employee['payroll_period'],
        'date': employee['date'] or get_current_date(), 
        'photo': employee['photo'],
        **calcs  # Unpacks salary, sss, philhealth, pagibig, total_deductions, net_salary
    }

    return render_template('payroll.html', employee=salary_details)

# 📄 Download PDF payslip
@app.route('/download/payroll/<int:emp_id>')
@login_required
def download_payroll_pdf(emp_id):
    employee = get_employee_by_id(emp_id)
    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for('dashboard'))

    # Use centralized calculator
    calcs = calculate_salary(employee['salary'])
    
    salary_details = {
        'id': employee['id'],
        'name': employee['name'],
        'position': employee['position'],
        'department': employee['department'],
        'payroll_period': employee['payroll_period'],
        'date': employee['date'] or get_current_date(),
        **calcs
    }

    # Render HTML template for the PDF content
    pdf_html = render_template('payroll_pdf.html', employee=salary_details)
    
    # Generate PDF from HTML
    pdf_file = generate_payroll_pdf(pdf_html)
    
    if pdf_file:
        response = make_response(pdf_file)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=payroll_{employee["name"]}.pdf'
        return response
    else:
        flash('Error generating PDF.', 'danger')
        return redirect(url_for('view_payroll', emp_id=emp_id))


# 📊 Export payroll data to CSV
@app.route('/dashboard/export', methods=['GET'])
@login_required
def export_payroll_csv():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Fetch only necessary data for the report
    c.execute('SELECT id, name, position, salary FROM employees')
    rows = c.fetchall()
    conn.close()

    # Create CSV in-memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write Header
    writer.writerow(['ID', 'Name', 'Position', 'Salary', 'SSS', 'PhilHealth', 'Pag-IBIG', 'Net Pay'])
    
    # Write Data Rows
    for emp_id, name, position, salary in rows:
        # Use the centralized calculator
        calcs = calculate_salary(salary)
        writer.writerow([
            emp_id,
            name,
            position,
            f"{calcs['salary']:.2f}",
            f"{calcs['sss']:.2f}",
            f"{calcs['philhealth']:.2f}",
            f"{calcs['pagibig']:.2f}",
            f"{calcs['net_salary']:.2f}"
        ])

    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=payroll_export.csv'
    return response


# --- Admin Routes ---

@app.route('/admin/approvals')
@login_required
@admin_required
def admin_approvals():
    # This is a placeholder. Implement approval logic if needed.
    # This template will be fixed by the Bootstrap CSS link in base.html
    return render_template('admin_approvals.html')

# --- Main Dashboard Route ---

# 📊 Dashboard View (This is the primary dashboard)
@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Ensure we can access columns by name
    c = conn.cursor()

    # Fetch all employees for "Recent Employees" card
    c.execute('SELECT * FROM employees ORDER BY date DESC') # Order by date for "Recent"
    employee_rows = c.fetchall()
    
    # Convert rows to a list of dictionaries
    employees = [dict(row) for row in employee_rows]

    # Calculate totals for stat cards
    total_employees = len(employees)
    total_salary = sum(emp['salary'] for emp in employees if emp['salary'])

    conn.close()
    
    # --- UPDATE ---
    # Removed all the unused logic for department/position charts
    # and aggregated deductions (total_sss, net_total, etc.)
    # as they are not used in the dashboard.html template.
    # The template only needs total_employees, total_salary,
    # and the list of employees.
    # ----------------

    return render_template('dashboard.html',
                           employees=employees,
                           total_employees=total_employees,
                           total_salary=f'{total_salary:,.2f}')


# --- Initialization ---
if __name__ == '__main__':
    init_db()  # Ensure tables are created before running
    app.run(debug=True)