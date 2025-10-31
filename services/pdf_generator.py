import io
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas

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

def generate_payroll_pdf(emp):
    # 📦 Fetch employee data (emp is already a dictionary-like object)
    emp_id = emp['id']
    payroll_period = emp['payroll_period']

    # 📊 Fetch attendance and loan data
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT * FROM attendance WHERE employee_id = ? AND payroll_period = ?', (emp_id, payroll_period))
    att = c.fetchone()
    overtime_hours = att['overtime_hours'] if att else 0
    absences = att['absences'] if att else 0

    c.execute('SELECT loan FROM deductions WHERE employee_id = ? AND payroll_period = ?', (emp_id, payroll_period))
    ded = c.fetchone()
    loan = ded['loan'] if ded else 0

    conn.close()

    # 💰 Calculations
    salary = float(emp['salary'])

    # Use hourly_rate from employee record if available, else calculate
    if emp['hourly_rate'] and emp['hourly_rate'] > 0:
         hourly_rate = float(emp['hourly_rate'])
    else:
         hourly_rate = salary / 22 / 8  # Default calculation

    overtime_pay = overtime_hours * hourly_rate * 1.25
    absence_deduction = absences * 8 * hourly_rate
    gross_pay = salary + overtime_pay - absence_deduction

    sss = salary * 0.01
    philhealth = salary * 0.015
    pagibig = salary * 0.01
    total_deductions = sss + philhealth + pagibig + loan + absence_deduction
    net_pay = gross_pay - total_deductions

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
        ['Gross Pay', f"PHP {gross_pay:,.2f}"],
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

    # 📦 Build PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    doc.build(elements, canvasmaker=CustomCanvas)
    buffer.seek(0)

    return buffer