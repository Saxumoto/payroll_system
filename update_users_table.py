import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Check if 'status' column exists
c.execute("PRAGMA table_info(users)")
columns = [col[1] for col in c.fetchall()]

if 'status' not in columns:
    c.execute('ALTER TABLE users ADD COLUMN status TEXT DEFAULT "approved"')
    print("Added 'status' column to users table.")
else:
    print("'status' column already exists.")

conn.commit()
conn.close()