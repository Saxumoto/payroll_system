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

def generate_payslip_pdf(emp):
    # 📊 Fetch attendance and loan data
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT * FROM attendance WHERE employee_id = ? AND payroll_period = ?', (emp['id'], emp['payroll_period']))
    att = c.fetchone()
    overtime_hours = att['overtime_hours'] if att else 0
    absences = att['absences'] if att else 0

    c.execute('SELECT loan FROM deductions WHERE employee_id = ? AND payroll_period = ?', (emp['id'], emp['payroll_period']))
    ded = c.fetchone()
    loan = ded['loan'] if ded else 0

    conn.close()

    # 💰 Calculations
    salary = float(emp['salary'])
    hourly_rate = salary / 22 / 8
    overtime_pay = overtime_hours