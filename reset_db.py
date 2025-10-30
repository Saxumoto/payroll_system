import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Delete all employee records
c.execute('DELETE FROM employees')

# Reset auto-increment counter
c.execute('DELETE FROM sqlite_sequence WHERE name="employees"')

conn.commit()
conn.close()

print("Database reset complete.")