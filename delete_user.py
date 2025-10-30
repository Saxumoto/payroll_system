import sqlite3

def delete_user(username):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE username = ?', (username,))
    conn.commit()
    conn.close()
    print(f"User '{username}' deleted.")

# 🔧 Replace with the username you want to delete
delete_user('admin')