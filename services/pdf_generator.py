import io
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
import models # We need to import models to fetch related data

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

def create_pdf_from_payroll_data(emp):
    """
    Generates a PDF using ReportLab based on calculated employee data.
    'emp' must be the calculated payroll dict from utils.calculate_payroll.
    """
    # 📄 PDF setup
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    elements = []

    # 🏷️ Header
    elements.append(Paragraph("<b>The Visa Center - Davao</b>", styles['Title']))
    elements.append(Paragraph("<b>Employee Payslip</b>", styles['Heading2']))
    elements.append(Spacer(1, 12))

    # 👤 Employee Info Table
    info_data = [
        ['Employee Name', emp['name']],
        ['Position', emp['position']],
        ['Department', emp['department']],
        ['Pay Period', f"{emp['pay_period_start']} to {emp['pay_period_end']}"],
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
    # NOTE: The data structure here must match the data passed from app.py/utils.py
    salary_data = [
        ['', 'Amount (PHP)'],
        ['Earnings', ''],
        ['Base Salary', f"{emp['salary']:,.2f}"],
        [f"Regular Pay ({emp['total_regular_hours']:,.2f} hrs)", f"{emp['regular_pay']:,.2f}"],
        [f"Overtime Pay ({emp['total_overtime_hours']:,.2f} hrs)", f"{emp['overtime_pay']:,.2f}"],
        ['Deductions', ''],
        ['SSS Contribution', f"({emp['sss']:,.2f})"],
        ['PhilHealth Contribution', f"({emp['philhealth']:,.2f})"],
        ['Pag-IBIG Contribution', f"({emp['pagibig']:,.2f})"],
        ['Withholding Tax (EWT)', f"({emp['tax']:,.2f})"],
        ['Loan Deductions', f"({emp['loan_deductions']:,.2f})"],
        ['', ''],
        ['Total Deductions', f"PHP ({emp['total_deductions']:,.2f})"],
        ['NET PAY', f"PHP {emp['net_salary']:,.2f}"],
    ]
    salary_table = Table(salary_data, colWidths=[200, 100])
    salary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('SPAN', (0, 1), (1, 1)),
        ('SPAN', (0, 5), (1, 5)),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, 12), (-1, 12), 1, colors.black),
        ('FONTNAME', (0, 13), (-1, 13), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 13), (-1, 13), colors.yellowgreen),
        ('LEFTPADDING', (0, 2), (0, 4), 20), # Indent earnings
        ('LEFTPADDING', (0, 6), (0, 10), 20), # Indent deductions
    ]))
    elements.append(salary_table)
    elements.append(Spacer(1, 24))

    # 📝 Footer
    elements.append(Paragraph("This is a system-generated payslip. No signature required.", styles['Normal']))

    # 📦 Build PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    doc.build(elements, canvasmaker=CustomCanvas)
    buffer.seek(0)

    # Return the byte stream
    return buffer.read()

# NOTE: The name 'generate_pdf_from_html' is what app.py is looking for.
# We map it to our new function that uses ReportLab's data structure.
generate_pdf_from_html = create_pdf_from_payroll_data
