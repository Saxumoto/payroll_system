import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Show all columns in the users table
c.execute("PRAGMA table_info(users)")
columns = c.fetchall()
conn.close()

for col in columns:
    print(col)