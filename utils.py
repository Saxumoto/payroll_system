def calculate_salary(emp_id, payroll_period=None):
    import sqlite3

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fetch employee record
    if payroll_period:
        c.execute('SELECT id, name, position, department, salary FROM employees WHERE id = ? AND payroll_period = ?', (emp_id, payroll_period))
    else:
        c.execute('SELECT id, name, position, department, salary FROM employees WHERE id = ?', (emp_id,))
    
    emp = c.fetchone()
    conn.close()

    if not emp:
        return None

    salary = float(emp['salary'])

    # Statutory deductions (2025 rates)
    sss = salary * 0.01
    philhealth = salary * 0.015
    pagibig = salary * 0.01

    # Placeholder for withholding tax (can be expanded later)
    withholding_tax = 0

    # Net salary
    net_salary = salary - (sss + philhealth + pagibig + withholding_tax)

    return {
        'id': emp['id'],
        'name': emp['name'],
        'position': emp['position'],
        'department': emp['department'],
        'salary': round(salary, 2),
        'sss': round(sss, 2),
        'philhealth': round(philhealth, 2),
        'pagibig': round(pagibig, 2),
        'withholding_tax': round(withholding_tax, 2),
        'net_salary': round(net_salary, 2)
    }

def process_payroll_period(payroll_period):
    import sqlite3

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fetch all employees for the selected period
    c.execute('SELECT * FROM employees WHERE payroll_period = ?', (payroll_period,))
    employees = c.fetchall()
    conn.close()

    payroll_data = []
    for emp in employees:
        salary = float(emp['salary'])
        sss = salary * 0.01
        philhealth = salary * 0.015
        pagibig = salary * 0.01
        net_salary = salary - (sss + philhealth + pagibig)

        payroll_data.append({
            'id': emp['id'],
            'name': emp['name'],
            'position': emp['position'],
            'department': emp['department'],
            'salary': round(salary, 2),
            'sss': round(sss, 2),
            'philhealth': round(philhealth, 2),
            'pagibig': round(pagibig, 2),
            'net_salary': round(net_salary, 2),
            'payroll_period': payroll_period
        })

    return payroll_data