import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Update the role of admin123 to 'admin'
c.execute('UPDATE users SET role = "admin" WHERE username = "admin123"')

conn.commit()
conn.close()
print("User 'admin123' is now tagged as admin.")