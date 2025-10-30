# 📦 Core Flask & Extensions
from flask import (
    Flask, render_template, request, redirect,
    make_response, send_file, flash, url_for
)
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user
)

# 🧠 Models & Business Logic
from models import (
    init_db, add_employee, get_employees, get_employee_by_id,
    update_employee, delete_employee, get_user_by_username,
    User, add_user
)
from utils import calculate_salary

# 📄 PDF & File Handling
import pdfkit
import sqlite3
import csv
import io
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

# 📁 File System & UUID
import os
import uuid

# 🖨️ ReportLab for PDF Generation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas

class CustomCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAuthor("The Visa Center - Davao")
        self.setTitle("Employee Payslip")
        self.setSubject("Payroll Document")

# 🧾 Modular PDF Generator
from services.pdf_generator import generate_payslip_pdf

# 📅 Date Utilities
from datetime import datetime

# 🚀 Initialize Flask App
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default-secret-key")
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# 📊 Attendance & Leave Integration (coming soon)
# from services.attendance_importer import import_attendance_csv
# from services.leave_manager import calculate_leave_deductions
# 🕒 Inject current year into templates
@app.context_processor
def inject_year():
    return {'current_year': datetime.now().year}

# 🖨️ Custom Canvas for PDF Metadata
class CustomCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAuthor("The Visa Center - Davao")
        self.setTitle("Employee Payslip")
        self.setSubject("Payroll Document")

# 📅 Utility: Get current date as string
def get_current_date():
    return datetime.now().strftime('%Y-%m-%d')  # Format: 2025-10-30
# 🔧 Initialize database
init_db()

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 🔐 Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return User(*row) if row else None

# 🏠 Landing page
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/')
def root():
    return redirect('/home')

# 🔐 Login (admin only)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)

        if not user:
            return "User not found."
        if user.role != 'admin':
            return "Access denied. Only admin accounts are allowed."
        if check_password_hash(user.password, password):
            login_user(user)
            return redirect('/dashboard')
        return "Invalid credentials."

    return render_template('login.html')

# 📝 Register (admin only)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if get_user_by_username(username):
            return "Username already taken."
        add_user(username, password, role='admin', status='approved')
        return redirect('/login')
    return render_template('register.html')

# 🔓 Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# 👥 Employee Management Page
@app.route('/employees')
@login_required
def employees():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fetch employee data
    c.execute('SELECT id, name, position, salary, payroll_period FROM employees ORDER BY id ASC')
    employees = c.fetchall()

    # Backend calculations
    total_employees = len(employees)
    total_salary = sum(float(emp['salary']) for emp in employees)
    total_sss = sum(float(emp['salary']) * 0.01 for emp in employees)
    total_philhealth = sum(float(emp['salary']) * 0.015 for emp in employees)
    total_pagibig = sum(float(emp['salary']) * 0.01 for emp in employees)
    net_total = total_salary - total_sss - total_philhealth - total_pagibig

    conn.close()

    return render_template(
        'employees.html',
        employees=employees,
        total_employees=total_employees,
        total_salary=total_salary,
        total_sss=total_sss,
        total_philhealth=total_philhealth,
        total_pagibig=total_pagibig,
        net_total=net_total
    )
    
# ➕ Add employee
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form['name']
        position = request.form['position']
        department = request.form['department']
        payroll_period = request.form['payroll_period'].strip().title()  # e.g. "October 2025"
        salary = float(request.form['salary'])
        date = request.form.get('date') or get_current_date()
        photo_file = request.files['photo']
        hourly_rate = request.form.get('hourly_rate', type=float)

        # Ensure upload folder exists
        upload_folder = os.path.join('static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        # Save photo with unique filename
        photo_filename = str(uuid.uuid4()) + os.path.splitext(secure_filename(photo_file.filename))[1]
        photo_path = os.path.join(upload_folder, photo_filename)
        photo_file.save(photo_path)

        # Save to database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO employees (name, position, department, payroll_period, salary, date, photo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, position, department,  hourly_rate, payroll_period, salary, date, photo_filename))
        conn.commit()
        conn.close()

        flash("Employee added successfully.", "success")
        return redirect('/payroll')

    return render_template('add_employee.html')

 # ✏️ Edit employee
@app.route('/edit/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    import os, uuid
    from werkzeug.utils import secure_filename

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fetch employee record
    c.execute('SELECT * FROM employees WHERE id = ?', (employee_id,))
    employee = c.fetchone()

    if not employee:
        conn.close()
        flash("Employee not found.", "danger")
        return redirect('/dashboard')

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
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            photo_filename = str(uuid.uuid4()) + os.path.splitext(secure_filename(photo_file.filename))[1]
            photo_path = os.path.join(upload_folder, photo_filename)
            photo_file.save(photo_path)

        # Update employee record
        c.execute('''
            UPDATE employees
            SET name = ?, position = ?, department = ?, salary = ?, payroll_period = ?, date = ?, photo = ?
            WHERE id = ?
        ''', (name, position, department, salary, hourly_rate, payroll_period, date, photo_filename, employee_id))
        conn.commit()
        conn.close()

        flash("Employee updated successfully.", "success")
        return redirect('/dashboard')

    conn.close()
    return render_template('edit_employee.html', employee=employee)

# ❌ Delete employee
@app.route('/delete/<int:emp_id>', methods=['POST'])
@login_required
def delete(emp_id):
    if current_user.role != 'admin':
        flash("Access denied. Admins only.", "danger")
        return redirect('/employees')

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fetch photo filename
    c.execute('SELECT photo FROM employees WHERE id = ?', (emp_id,))
    row = c.fetchone()
    if row and row['photo']:
        photo_path = os.path.join('static', 'uploads', row['photo'])
        if os.path.exists(photo_path):
            os.remove(photo_path)

    # Delete employee record
    c.execute('DELETE FROM employees WHERE id = ?', (emp_id,))
    conn.commit()
    conn.close()

    flash("Employee deleted successfully.", "info")
    return redirect('/employees')

# 📄 View payslip
# 📄 Individual Payslip View
@app.route('/payroll/<int:emp_id>')
@login_required
def view_payslip(emp_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fetch employee record
    c.execute('SELECT * FROM employees WHERE id = ?', (emp_id,))
    employee = c.fetchone()
    conn.close()

    if not employee:
        flash("Employee not found.", "danger")
        return redirect('/payroll')

    # Calculate deductions
    salary = float(employee['salary'])
    sss = round(salary * 0.01, 2)
    philhealth = round(salary * 0.015, 2)
    pagibig = round(salary * 0.01, 2)
    net_salary = salary - sss - philhealth - pagibig

    # Prepare details dictionary
    salary_details = {
        'id': employee['id'],
        'name': employee['name'],
        'position': employee['position'],
        'department': employee['department'],
        'payroll_period': employee['payroll_period'],
        'date': employee['date'] or get_current_date(), 
        'date': employee['date'],
        'salary': salary,
        'sss': sss,
        'philhealth': philhealth,
        'pagibig': pagibig,
        'net_salary': net_salary,
        'photo': employee['photo']
    }

    return render_template('payroll.html', details=salary_details)

# 📄 Payroll Dashboard with Filtering
@app.route('/payroll', methods=['GET', 'POST'])
@login_required
def payroll_dashboard():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get distinct payroll periods (normalized)
    c.execute('SELECT DISTINCT payroll_period FROM employees ORDER BY payroll_period DESC')
    periods = [row['payroll_period'].title() for row in c.fetchall()]

    # Get selected period from form
    selected_period = request.args.get('payroll_period')

    if selected_period:
        c.execute('SELECT * FROM employees WHERE payroll_period = ?', (selected_period,))
    else:
        c.execute('SELECT * FROM employees ORDER BY payroll_period DESC')

    employees = c.fetchall()
    conn.close()

    return render_template('payroll_dashboard.html', employees=employees, periods=periods, selected_period=selected_period)

# 📤 Export payroll to CSV
@app.route('/dashboard/export', methods=['POST'])
@login_required
def export_csv():
    if current_user.role != 'admin':
        return "Access denied."

    selected_period = request.form.get('period')
    if not selected_period:
        return "No payroll period selected."

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id, name, position, salary FROM employees WHERE payroll_period = ?', (selected_period,))
    rows = c.fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Position', 'Salary', 'SSS', 'PhilHealth', 'Pag-IBIG', 'Net Salary'])

    for emp_id, name, position, salary in rows:
        salary = salary or 0
        sss = salary * 0.01
        philhealth = salary * 0.015
        pagibig = salary * 0.01
        net_salary = salary - (sss + philhealth + pagibig)
        writer.writerow([
            emp_id,
            name,
            position,
            f"{salary:.2f}",
            f"{sss:.2f}",
            f"{philhealth:.2f}",
            f"{pagibig:.2f}",
            f"{net_salary:.2f}"
        ])

    safe_period = selected_period.replace(" ", "_").replace("/", "-")
    filename = f"payroll_{safe_period}.csv"

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv'
    return response

# 📄 View employee details
@app.route('/employee/<int:employee_id>')
@login_required
def view_employee(employee_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Enables dict-style access
    c = conn.cursor()
    c.execute('SELECT * FROM employees WHERE id = ?', (employee_id,))
    employee = c.fetchone()
    conn.close()

    if not employee:
        return "Employee not found."

    return render_template('view_employee.html', employee=employee)

# 📊 Admin Dashboard with Employee Management
@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get available payroll periods
    c.execute('SELECT DISTINCT payroll_period FROM employees WHERE payroll_period IS NOT NULL ORDER BY payroll_period DESC')
    periods = [row[0] for row in c.fetchall()]

    # Get available departments
    c.execute('SELECT DISTINCT department FROM employees WHERE department IS NOT NULL ORDER BY department')
    departments = [row[0] for row in c.fetchall()]

    # Get selected filters from query string
    selected_period = request.args.get('period') or (periods[0] if periods else None)
    selected_department = request.args.get('department_filter') or ''

    # Build query with filters
    query = 'SELECT id, name, position, department, salary, payroll_period FROM employees WHERE 1=1'
    params = []

    if selected_period:
        query += ' AND payroll_period = ?'
        params.append(selected_period)

    if selected_department:
        query += ' AND department = ?'
        params.append(selected_department)

    c.execute(query, params)
    employees = [dict(row) for row in c.fetchall()]

    # Initialize totals
    total_employees = len(employees)
    total_salary = sum(emp['salary'] or 0 for emp in employees)
    total_sss = 0
    total_philhealth = 0
    total_pagibig = 0
    net_total = 0

    # Calculate deductions and net pay
    for emp in employees:
        salary = emp['salary'] or 0
        sss = salary * 0.01
        philhealth = salary * 0.015
        pagibig = salary * 0.01
        net_salary = salary - (sss + philhealth + pagibig)

        emp['net_salary'] = net_salary
        emp['sss'] = sss
        emp['philhealth'] = philhealth
        emp['pagibig'] = pagibig

        total_sss += sss
        total_philhealth += philhealth
        total_pagibig += pagibig
        net_total += net_salary

    conn.close()

    return render_template('dashboard.html',
        total_employees=total_employees,
        total_payroll=total_salary,
        total_deduction=total_sss + total_philhealth + total_pagibig,
        net_pay=net_total,
        total_contribution=total_philhealth + total_pagibig,
        total_loan=0,  # Update if you track loans
        employees=employees,
        periods=periods,
        departments=departments,
        selected_period=selected_period,
        selected_department=selected_department
    )# 📊 Employee Breakdown View
@app.route('/dashboard')
@login_required
def employee_dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Fetch employee breakdown data
    c.execute('''
        SELECT id, name, position, department, salary, payroll_period
        FROM employees
        ORDER BY payroll_period DESC
    ''')
    employees = c.fetchall()

    conn.close()
    return render_template('dashboard.html', employees=employees)

# 📄 Download Payslip as PDF
@app.route('/payroll/<int:emp_id>/pdf')
@login_required
def download_payslip_pdf(emp_id):
    import sqlite3, io
    from flask import send_file, flash, redirect
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfgen import canvas

    # 📦 Fetch employee data
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM employees WHERE id = ?', (emp_id,))
    emp = c.fetchone()

    if not emp:
        conn.close()
        flash("Employee not found.", "danger")
        return redirect('/payroll')

    # 📊 Fetch attendance and loan data
    c.execute('SELECT * FROM attendance WHERE employee_id = ? AND payroll_period = ?', (emp_id, emp['payroll_period']))
    att = c.fetchone()
    overtime_hours = att['overtime_hours'] if att else 0
    absences = att['absences'] if att else 0

    c.execute('SELECT loan FROM deductions WHERE employee_id = ? AND payroll_period = ?', (emp_id, emp['payroll_period']))
    ded = c.fetchone()
    loan = ded['loan'] if ded else 0

    conn.close()

    # 💰 Calculations
    salary = float(emp['salary'])
    hourly_rate = salary / 22 / 8
    overtime_pay = overtime_hours * hourly_rate * 1.25
    absence_deduction = absences * 8 * hourly_rate
    gross_pay = salary + overtime_pay - absence_deduction

    sss = salary * 0.01
    philhealth = salary * 0.015
    pagibig = salary * 0.01
    net_pay = gross_pay - (sss + philhealth + pagibig + loan)

    # Round values
    salary = round(salary, 2)
    overtime_pay = round(overtime_pay, 2)
    absence_deduction = round(absence_deduction, 2)
    gross_pay = round(gross_pay, 2)
    sss = round(sss, 2)
    philhealth = round(philhealth, 2)
    pagibig = round(pagibig, 2)
    loan = round(loan, 2)
    net_pay = round(net_pay, 2)

    # 📄 PDF setup
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    elements = []

    # 🏷️ Header
    elements.append(Paragraph("The Visa Center - Davao", styles['Title']))
    elements.append(Paragraph("Employee Payslip", styles['Heading2']))
    elements.append(Spacer(1, 12))

    # 👤 Employee Info Table
    info_data = [
        ['Employee Name', emp['name']],
        ['Position', emp['position']],
        ['Department', emp['department']],
        ['Payroll Period', emp['payroll_period']],
    ]
    info_table = Table(info_data, colWidths=[150, 300])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 12))

    # 💸 Salary Breakdown Table
    salary_data = [
        ['Basic Salary', f"PHP {salary:,.2f}"],
        ['Overtime Pay', f"PHP {overtime_pay:,.2f}"],
        ['Absence Deduction', f"PHP {absence_deduction:,.2f}"],
        ['SSS Deduction', f"PHP {sss:,.2f}"],
        ['PhilHealth Deduction', f"PHP {philhealth:,.2f}"],
        ['Pag-IBIG Deduction', f"PHP {pagibig:,.2f}"],
        ['Loan Deduction', f"PHP {loan:,.2f}"],
        ['Net Pay', f"PHP {net_pay:,.2f}"],
    ]
    salary_table = Table(salary_data, colWidths=[200, 250])
    salary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(salary_table)
    elements.append(Spacer(1, 24))

    # 📝 Footer
    elements.append(Paragraph("This is a system-generated payslip. No signature required.", styles['Normal']))

    # 🖨️ Metadata Canvas
    class CustomCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._set_metadata()

        def _set_metadata(self):
            self.setAuthor("The Visa Center - Davao")
            self.setTitle("Employee Payslip")
            self.setSubject("Payroll Document")

        def showPage(self):
            self._set_metadata()
            super().showPage()

        def save(self):
            self._set_metadata()
            super().save()

    # 📦 Build PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    doc.build(elements, canvasmaker=CustomCanvas)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"payslip_{emp_id}.pdf", mimetype='application/pdf')

# 📄 Bulk Payslip Generation for Payroll Period
@app.route('/payroll/payslips/<period>')
@login_required
def generate_bulk_payslips(period):
    import zipfile
    import os
    from datetime import datetime

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM employees WHERE payroll_period = ?', (period,))
    employees = c.fetchall()
    conn.close()

    if not employees:
        flash("No employees found for this payroll period.", "warning")
        return redirect('/payroll')

    # Create a temporary ZIP archive
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for emp in employees:
            emp_id = emp['id']
            name = emp['name']
            filename = f"{name.replace(' ', '_')}_payslip.pdf"

            # Generate individual PDF
            pdf_buffer = generate_payslip_pdf(emp)  # You’ll define this next
            zipf.writestr(filename, pdf_buffer.getvalue())

    zip_buffer.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return send_file(zip_buffer, as_attachment=True, download_name=f"payslips_{period}_{timestamp}.zip", mimetype='application/zip')

# 📤 Upload Attendance CSV
@app.route('/upload-attendance', methods=['POST'])
@login_required
def upload_attendance():
    file = request.files.get('attendance_file')
    if not file or not file.filename.endswith('.csv'):
        flash("Please upload a valid CSV file.", "danger")
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    reader = csv.DictReader(stream)

    for row in reader:
        try:
            c.execute('''
                INSERT INTO attendance (employee_id, date, clock_in, clock_out, total_hours)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                int(row['employee_id']),
                row['date'],
                row['clock_in'],
                row['clock_out'],
                float(row['total_hours'])
            ))
        except Exception as e:
            print("Error importing row:", row, e)

    conn.commit()
    conn.close()
    flash("Attendance data imported successfully.", "success")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)

