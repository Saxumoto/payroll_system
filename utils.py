"""
Utility functions for payroll calculations.
"""
import models
from datetime import date

# --- Deduction Functions (Updated) ---

def calculate_sss(salary):
    """
    Simplified SSS contribution calculation based on 2024 tables.
    Capped at 30,000 salary credit.
    """
    if salary >= 30000:
        employee_share = 1350.00
    elif salary < 4250:
        employee_share = 180.00
    else:
        # Simplified: 4.5% of salary
        employee_share = salary * 0.045
    return employee_share

def calculate_philhealth(salary):
    """
    Simplified PhilHealth contribution calculation (5% in 2024).
    Floor 10,000, Ceiling 100,000.
    """
    if salary > 100000:
        salary_credit = 100000
    elif salary < 10000:
        salary_credit = 10000
    else:
        salary_credit = salary
    
    total_premium = salary_credit * 0.05
    employee_share = total_premium / 2
    return employee_share

def calculate_pagibig(salary):
    """
    Simplified Pag-IBIG contribution calculation.
    """
    # 2% of salary, capped at 100
    employee_share = salary * 0.02
    if employee_share > 100:
        return 100.00
    return employee_share

def calculate_withholding_tax(salary, sss, philhealth, pagibig):
    """
    Calculates monthly withholding tax based on 2023-2025 BIR tables.
    """
    # Taxable income = Gross Income - SSS - PhilHealth - Pag-IBIG
    taxable_income = salary - (sss + philhealth + pagibig)

    # Calculate Tax
    tax = 0.0
    if taxable_income <= 20833:
        tax = 0.0
    elif taxable_income <= 33332:
        tax = (taxable_income - 20833) * 0.15
    elif taxable_income <= 66666:
        tax = 1875 + (taxable_income - 33333) * 0.20
    elif taxable_income <= 166666:
        tax = 8541.67 + (taxable_income - 66667) * 0.25
    elif taxable_income <= 666666:
        tax = 33541.67 + (taxable_income - 166667) * 0.30
    else:
        tax = 183541.67 + (taxable_income - 666667) * 0.35
    
    return tax

# --- Main Payroll Calculation (HEAVILY UPDATED) ---

def calculate_payroll(employee_data, start_date, end_date):
    """
    Calculates all deductions for a single employee based on time records.
    Accepts an employee's data (as a dict or sqlite3.Row) and a date range.
    """
    # Get base data
    hourly_rate = float(employee_data.get('hourly_rate') or 0.0)
    overtime_rate = hourly_rate * 1.5  # Common overtime rate
    
    # --- 1. Calculate Gross Pay from Time Records ---
    time_records = models.get_time_records(employee_data['id'], start_date, end_date)
    
    total_regular_hours = sum(r['hours_worked'] for r in time_records)
    total_overtime_hours = sum(r['overtime_hours'] for r in time_records)
    
    regular_pay = total_regular_hours * hourly_rate
    overtime_pay = total_overtime_hours * overtime_rate
    gross_pay = regular_pay + overtime_pay
    
    # --- 2. Calculate Deductions based on Gross Pay ---
    sss = calculate_sss(gross_pay)
    philhealth = calculate_philhealth(gross_pay)
    pagibig = calculate_pagibig(gross_pay)
    
    # Calculate withholding tax
    tax = calculate_withholding_tax(gross_pay, sss, philhealth, pagibig)
    
    # --- 3. Get Loan Deductions ---
    active_loans = models.get_active_loans(employee_data['id'])
    loan_deductions = 0.0
    # Note: This logic assumes loans are deducted monthly.
    # A real system would check if a deduction is due this pay period.
    for loan in active_loans:
        loan_deductions += loan['monthly_deduction']

    # --- 4. Final Calculation ---
    total_deductions = sss + philhealth + pagibig + tax + loan_deductions
    net_pay = gross_pay - total_deductions

    return {
        'salary': gross_pay,  # Rename 'salary' to 'gross_pay' for clarity
        'gross_pay': gross_pay,
        'regular_pay': regular_pay,
        'overtime_pay': overtime_pay,
        'total_regular_hours': total_regular_hours,
        'total_overtime_hours': total_overtime_hours,
        'sss': sss,
        'philhealth': philhealth,
        'pagibig': pagibig,
        'tax': tax,
        'loan_deductions': loan_deductions,
        'total_deductions': total_deductions,
        'net_salary': net_pay
    }

def get_payroll_totals(employees, start_date, end_date):
    """
    Calculates the total payroll amounts for all employees for a given period.
    Accepts a list of sqlite3.Row objects and a date range.
    """
    total_salary = 0.0
    total_sss = 0.0
    total_philhealth = 0.0
    total_pagibig = 0.0
    total_tax = 0.0
    total_net = 0.0

    for emp in employees:
        # calculate_payroll now needs the full employee row and dates
        payroll = calculate_payroll(emp, start_date, end_date)
        
        total_salary += payroll['gross_pay']
        total_sss += payroll['sss']
        total_philhealth += payroll['philhealth']
        total_pagibig += payroll['pagibig']
        total_tax += payroll['tax']
        total_net += payroll['net_salary']

    return {
        'total_salary': f"{total_salary:,.2f}",
        'total_sss': f"{total_sss:,.2f}",
        'total_philhealth': f"{total_philhealth:,.2f}",
        'total_pagibig': f"{total_pagibig:,.2f}",
        'total_tax': f"{total_tax:,.2f}",
        'net_total': f"{total_net:,.2f}"
    }