import datetime

def get_current_date():
    """Returns the current date in YYYY-MM-DD format."""
    return datetime.date.today().strftime('%Y-%m-%d')

def calculate_salary(base_salary):
    """
    Calculates deductions and net salary from a base salary.
    All payroll logic is centralized here.
    """
    # Ensure salary is a number, default to 0 if None or invalid
    if base_salary is None:
        base_salary = 0.0
    
    try:
        # Ensure base_salary is a float for calculations
        base_salary = float(base_salary)
    except (ValueError, TypeError):
        base_salary = 0.0

    # ---Deduction Calculations---
    # These values can be updated here and will apply everywhere.
    
    # SSS Contribution (example: 1% of base salary)
    sss = round(base_salary * 0.01, 2)
    
    # PhilHealth Contribution (example: 1.5% of base salary)
    philhealth = round(base_salary * 0.015, 2)
    
    # Pag-IBIG Contribution (example: 1% of base salary)
    pagibig = round(base_salary * 0.01, 2)
    
    # ---Totals---
    total_deductions = round(sss + philhealth + pagibig, 2)
    net_salary = round(base_salary - total_deductions, 2)
    
    # Return a dictionary with all values
    return {
        'salary': base_salary,
        'sss': sss,
        'philhealth': philhealth,
        'pagibig': pagibig,
        'total_deductions': total_deductions,
        'net_salary': net_salary
    }

if __name__ == '__main__':
    # Example usage for testing
    date = get_current_date()
    print(f"Current Date: {date}")
    
    salary_details = calculate_salary(50000)
    print("\nSalary Calculation Example (Base: 50000):")
    print(f"  Base Salary: {salary_details['salary']:.2f}")
    print(f"  SSS: {salary_details['sss']:.2f}")
    print(f"  PhilHealth: {salary_details['philhealth']:.2f}")
    print(f"  Pag-IBIG: {salary_details['pagibig']:.2f}")
    print(f"  Total Deductions: {salary_details['total_deductions']:.2f}")
    print(f"  Net Salary: {salary_details['net_salary']:.2f}")

    salary_details_none = calculate_salary(None)
    print("\nSalary Calculation Example (Base: None):")
    print(f"  Base Salary: {salary_details_none['salary']:.2f}")
    print(f"  Net Salary: {salary_details_none['net_salary']:.2f}")
