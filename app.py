from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, date
import csv
import io

# Import functions from our new models.py
import models

# Import calculation functions
from utils import calculate_payroll, get_payroll_totals

# Import PDF service
from services.pdf_generator import generate_pdf_from_html

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this to a random secret key
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

# --- Login Manager Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'danger'

# This is a simple User class for Flask-Login to use
class User(UserMixin):
    def __init__(self, user_row):
        self.id = user_row['id']
        self.username = user_row['username']
        self.is_admin = bool(user_row['is_admin'])
        self.employee_id = user_row['employee_id']

@login_manager.user_loader
def load_user(user_id):
    user_row = models.get_user_by_id(user_id)
    if user_row:
        return User(user_row)
    return None

# --- Helper Function ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# --- Public & Auth Routes ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_row = models.get_user_by_username(username)
        
        if user_row and check_password_hash(user_row['password_hash'], password):
            user_obj = User(user_row)
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        existing_user = models.get_user_by_username(username)
        if existing_user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        
        # Create a new user (default is not admin and no employee_id)
        models.create_user(username, password)
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/leave')
@login_required
def manage_leave():
    if not current_user.is_admin:
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('dashboard'))

    # Get pending requests
    pending_rows = models.get_leave_requests(status='Pending')
    pending_requests = []
    for req in pending_rows:
        emp = models.get_employee_by_id(req['employee_id'])
        req_dict = dict(req)
        req_dict['employee_name'] = emp['name'] if emp else 'Unknown'
        pending_requests.append(req_dict)

    # Get approved requests
    approved_rows = models.get_leave_requests(status='Approved')
    approved_requests = []
    for req in approved_rows:
        emp = models.get_employee_by_id(req['employee_id'])
        req_dict = dict(req)
        req_dict['employee_name'] = emp['name'] if emp else 'Unknown'
        approved_requests.append(req_dict)

    return render_template('manage_leave.html', 
                           pending_requests=pending_requests,
                           approved_requests=approved_requests)

#Leave status update route
@app.route('/leave/update/<int:leave_id>', methods=['POST'])
@login_required
def update_leave_status(leave_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))

    new_status = request.form.get('status')
    if new_status in ['Approved', 'Rejected']:
        models.update_leave_status(leave_id, new_status)
        flash(f'Leave request {new_status.lower()}!', 'success')
    else:
        flash('Invalid status.', 'danger')

    return redirect(url_for('manage_leave'))

# --- Main Application Routes ---

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        # Admin: Go to admin dashboard
        employees_rows = models.get_employees()
        
        # Define a pay period (e.g., the current month)
        today = date.today()
        start_date = today.replace(day=1)
        next_month = start_date.replace(month=start_date.month % 12 + 1)
        end_date = next_month - datetime.timedelta(days=1)
        
        totals = get_payroll_totals(employees_rows, start_date.isoformat(), end_date.isoformat())
        
        return render_template('dashboard.html', 
                               total_employees=len(employees_rows), 
                               total_salary=totals['total_salary'],
                               employees=employees_rows)
    else:
        # Not Admin: Go to employee dashboard
        return redirect(url_for('employee_dashboard'))

# --- User Management Route ---
@app.route('/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        employee_id = request.form.get('employee_id')
        is_admin = 1 if request.form.get('is_admin') else 0

        # Handle "Not Linked"
        if not employee_id:
            employee_id = None
        
        try:
            models.update_user_links(user_id, employee_id, is_admin)
            flash('User updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating user: {e}', 'danger')
        
        return redirect(url_for('manage_users'))

    # GET Request: Show the page
    users = models.get_all_users()
    employees = models.get_all_employees() # Get all, even inactive
    return render_template('manage_users.html', users=users, employees=employees)
# --- Employee-Facing Routes ---

@app.route('/my-dashboard')
@login_required
def employee_dashboard():
    if current_user.is_admin:
        # Admins should be at the admin dashboard
        return redirect(url_for('dashboard'))
    
    if not current_user.employee_id:
        flash('Your user account is not linked to an employee profile. Please contact admin.', 'danger')
        return redirect(url_for('logout'))

    employee = models.get_employee_by_id(current_user.employee_id)
    if not employee:
        flash('Employee profile not found. Please contact admin.', 'danger')
        return redirect(url_for('logout'))

    return render_template('employee_dashboard.html', employee_data=employee)

@app.route('/my-payslips')
@login_required
def employee_payslips():
    if current_user.is_admin:
        return redirect(url_for('dashboard'))
    if not current_user.employee_id:
        return redirect(url_for('logout'))
        
    employee = models.get_employee_by_id(current_user.employee_id)
    
    # --- Fetch historical payslips ---
    payslip_history = models.get_payslips_by_employee(current_user.employee_id)
    
    # --- Calculate Current (Un-processed) Payslip ---
    today = date.today()
    start_date = today.replace(day=1)
    next_month = start_date.replace(month=start_date.month % 12 + 1)
    end_date = next_month - datetime.timedelta(days=1)
    
    payroll_data = calculate_payroll(employee, start_date.isoformat(), end_date.isoformat())
    employee_data = dict(employee)
    employee_data.update(payroll_data)
    employee_data['pay_period_start'] = start_date.isoformat()
    employee_data['pay_period_end'] = end_date.isoformat()

    return render_template('employee_payslips.html', 
                           employee_data=employee, 
                           payslip=employee_data,
                           payslip_history=payslip_history) # Pass the history

@app.route('/my-leave', methods=['GET', 'POST'])
@login_required
def employee_leave():
    if current_user.is_admin:
        return redirect(url_for('dashboard'))
    if not current_user.employee_id:
        return redirect(url_for('logout'))
        
    employee = models.get_employee_by_id(current_user.employee_id)

    if request.method == 'POST':
        leave_type = request.form.get('leave_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        reason = request.form.get('reason')

        if not leave_type or not start_date or not end_date:
            flash('All fields are required to request leave.', 'danger')
        else:
            models.add_leave_request(current_user.employee_id, leave_type, start_date, end_date, reason)
            flash('Leave request submitted successfully!', 'success')
        
        return redirect(url_for('employee_leave'))

    # GET Request: Show the leave form and history
    my_requests = models.get_leave_requests(employee_id=current_user.employee_id, status=None) # Get all

    return render_template('employee_leave.html', 
                           employee_data=employee, 
                           my_requests=my_requests,
                           current_date=datetime.date.today().isoformat())

@app.route('/employees')
@login_required
def employee_list():
    # Define a pay period (e.g., the current month)
    today = date.today()
    start_date = today.replace(day=1)
    next_month = start_date.replace(month=start_date.month % 12 + 1)
    end_date = next_month - datetime.timedelta(days=1)
    
    employees_rows = models.get_employees()
    
    # Get all payroll data
    employees_with_payroll = []
    for emp_row in employees_rows:
        payroll_data = calculate_payroll(emp_row, start_date.isoformat(), end_date.isoformat())
        
        # Create a dictionary to pass to the template
        emp_dict = dict(emp_row)
        emp_dict.update(payroll_data)
        employees_with_payroll.append(emp_dict)
        
    totals = get_payroll_totals(employees_rows, start_date.isoformat(), end_date.isoformat())
    
    return render_template('employee_list.html', 
                           employees=employees_with_payroll, 
                           total_employees=len(employees_rows),
                           **totals) # Unpack all totals

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_employee_route():
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Get all form data from the updated template
        name = request.form['name']
        position = request.form['position']
        department = request.form['department']
        date_hired = request.form['date_hired']
        salary = request.form['salary']
        hourly_rate = request.form.get('hourly_rate') or 0.0
        payroll_period = request.form['payroll_period']
        
        contact_number = request.form.get('contact_number')
        address = request.form.get('address')
        bank_account_number = request.form.get('bank_account_number')
        tin_number = request.form.get('tin_number')
        sss_number = request.form.get('sss_number')
        philhealth_number = request.form.get('philhealth_number')
        pagibig_number = request.form.get('pagibig_number')
        
        photo = request.files.get('photo')
        photo_filename = 'default.png'
        if photo and allowed_file(photo.filename):
            photo_filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
        
        # Call the new add_employee function from models.py
        models.add_employee(
            name, position, department, salary, payroll_period, date_hired, 
            photo_filename, hourly_rate, contact_number, address, 
            bank_account_number, sss_number, philhealth_number, pagibig_number, tin_number
        )
        
        flash('Employee added successfully!', 'success')
        return redirect(url_for('employee_list'))

    return render_template('add_employee.html', 
                           current_date=datetime.date.today().isoformat())

@app.route('/edit/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))

    employee = models.get_employee_by_id(employee_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('employee_list'))

    if request.method == 'POST':
        # Get all form data from the updated template
        name = request.form['name']
        position = request.form['position']
        department = request.form['department']
        date_hired = request.form['date_hired']
        salary = request.form['salary']
        hourly_rate = request.form.get('hourly_rate') or 0.0
        payroll_period = request.form['payroll_period']
        
        contact_number = request.form.get('contact_number')
        address = request.form.get('address')
        bank_account_number = request.form.get('bank_account_number')
        tin_number = request.form.get('tin_number')
        sss_number = request.form.get('sss_number')
        philhealth_number = request.form.get('philhealth_number')
        pagibig_number = request.form.get('pagibig_number')
        
        photo_filename = employee['photo']
        photo = request.files.get('photo')
        if photo and allowed_file(photo.filename):
            photo_filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
        
        # Call the new update_employee function
        models.update_employee(
            employee_id, name, position, department, salary, payroll_period, date_hired, 
            photo_filename, hourly_rate, contact_number, address, 
            bank_account_number, sss_number, philhealth_number, pagibig_number, tin_number
        )
        
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employee_list'))

    # For GET request, pass the employee data to the template
    return render_template('edit_employee.html', employee=employee)

@app.route('/delete/<int:emp_id>', methods=['POST'])
@login_required
def delete_employee_route(emp_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('employee_list'))
        
    # Use the new archive_employee function
    models.archive_employee(emp_id)
    flash('Employee archived successfully.', 'success')
    return redirect(url_for('employee_list'))

@app.route('/payroll/<int:emp_id>')
@login_required
def view_payroll(emp_id):
    employee = models.get_employee_by_id(emp_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('employee_list'))
    
    # Define a pay period (e.g., the current month)
    today = date.today()
    start_date = today.replace(day=1)
    next_month = start_date.replace(month=start_date.month % 12 + 1)
    end_date = next_month - datetime.timedelta(days=1)
    
    # We now pass the full employee row and date range
    payroll_data = calculate_payroll(employee, start_date.isoformat(), end_date.isoformat())
    
    # Combine employee dict and payroll dict
    employee_data = dict(employee)
    employee_data.update(payroll_data)

    # Pass dates to template
    employee_data['pay_period_start'] = start_date.isoformat()
    employee_data['pay_period_end'] = end_date.isoformat()

    return render_template('payroll.html', employee=employee_data)
#Loan Management Route
@app.route('/loans/<int:emp_id>', methods=['GET', 'POST'])
@login_required
def manage_loans(emp_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    employee = models.get_employee_by_id(emp_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('employee_list'))

    if request.method == 'POST':
        # Add a new loan
        loan_name = request.form.get('loan_name')
        total_amount = request.form.get('total_amount')
        monthly_deduction = request.form.get('monthly_deduction')

        if not total_amount or not monthly_deduction:
            flash('All loan fields are required.', 'danger')
        else:
            try:
                models.add_loan(emp_id, loan_name, float(total_amount), float(monthly_deduction))
                flash('Loan added successfully!', 'success')
            except Exception as e:
                flash(f'Error adding loan: {e}', 'danger')
        
        return redirect(url_for('manage_loans', emp_id=emp_id))

    # GET Request: Show the page
    active_loans = models.get_active_loans(emp_id)
    return render_template('manage_loans.html', employee=employee, loans=active_loans)

#Attendance Management Route
@app.route('/attendance/<int:emp_id>', methods=['GET', 'POST'])
@login_required
def manage_attendance(emp_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    employee = models.get_employee_by_id(emp_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('employee_list'))

    if request.method == 'POST':
        date = request.form.get('date')
        hours_worked = request.form.get('hours_worked')
        overtime_hours = request.form.get('overtime_hours')

        if not date or not hours_worked:
            flash('Date and Hours Worked are required.', 'danger')
        else:
            try:
                models.add_time_record(emp_id, date, float(hours_worked), float(overtime_hours))
                flash('Time record added successfully!', 'success')
            except Exception as e:
                flash(f'Error adding time record: {e}', 'danger')
        
        return redirect(url_for('manage_attendance', emp_id=emp_id))

    # GET Request: Show the page
    # Fetch recent time records
    # For now, we just get all. A real app might paginate or limit by date.
    time_records = models.get_time_records(emp_id, '1900-01-01', '2100-01-01')
    
    return render_template('manage_attendance.html', 
                           employee=employee, 
                           time_records=time_records[-30:], # Show last 30
                           current_date=datetime.date.today().isoformat())

@app.route('/export/csv')
@login_required
def export_payroll_csv():
    employees_rows = models.get_employees()
    
    # Prepare data for CSV
    data = []
    headers = [
        'ID', 'Name', 'Position', 'Department', 'Base Salary', 
        'SSS', 'PhilHealth', 'Pag-IBIG', 'Total Deductions', 'Net Pay'
    ]
    data.append(headers)
    
    for emp in employees_rows:
        payroll = calculate_payroll(emp['salary'])
        data.append([
            emp['id'],
            emp['name'],
            emp['position'],
            emp['department'],
            emp['salary'],
            payroll['sss'],
            payroll['philhealth'],
            payroll['pagibig'],
            payroll['total_deductions'],
            payroll['net_salary']
        ])

    # Create CSV in memory
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerows(data)
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=payroll_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/download/pdf/<int:emp_id>')
@login_required
def download_payroll_pdf(emp_id):
    employee = models.get_employee_by_id(emp_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('employee_list'))
        
    # Define a pay period (e.g., the current month)
    today = date.today()
    start_date = today.replace(day=1)
    next_month = start_date.replace(month=start_date.month % 12 + 1)
    end_date = next_month - datetime.timedelta(days=1)
    
    payroll_data = calculate_payroll(employee, start_date.isoformat(), end_date.isoformat())
    
    # Combine employee dict and payroll dict
    employee_data = dict(employee)
    employee_data.update(payroll_data)

    # Pass dates to data structure
    employee_data['pay_period_start'] = start_date.isoformat()
    employee_data['pay_period_end'] = end_date.isoformat()

    # Generate PDF using the ReportLab function and the calculated data
    pdf_file = generate_pdf_from_html(employee_data)
    
    if pdf_file:
        response = make_response(pdf_file)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=payslip_{employee["name"]}.pdf'
        return response
    else:
        flash('Error generating PDF. Check server logs for details (Ensure ReportLab dependencies are met).', 'danger')
        return redirect(url_for('view_payroll', emp_id=emp_id))

#Payroll Processing Route
@app.route('/payroll/process', methods=['POST'])
@login_required
def process_payroll():
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))

    # Define the pay period (e.g., the current month)
    today = date.today()
    start_date = today.replace(day=1)
    next_month = start_date.replace(month=start_date.month % 12 + 1)
    end_date = next_month - datetime.timedelta(days=1)
    
    employees = models.get_employees()
    
    try:
        for emp in employees:
            # 1. Calculate the payroll
            payroll_data = calculate_payroll(emp, start_date.isoformat(), end_date.isoformat())
            
            # 2. Save the historical payslip
            models.create_payslip(
                emp['id'], 
                start_date.isoformat(), 
                end_date.isoformat(), 
                payroll_data
            )
            
            # 3. Update any active loans
            if payroll_data['loan_deductions'] > 0:
                active_loans = models.get_active_loans(emp['id'])
                for loan in active_loans:
                    # This assumes the full monthly deduction is paid
                    # A more complex system would prorate this
                    models.update_loan_payment(loan['id'], loan['monthly_deduction'])

        flash(f'Payroll processed successfully for {len(employees)} employees!', 'success')
    except Exception as e:
        flash(f'An error occurred: {e}', 'danger')
        
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Initialize the database if run directly (optional, but good for setup)
    models.init_db()
    app.run(debug=True)