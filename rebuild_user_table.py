import sqlite3
import sys

def rebuild_users_table():
    """
    Safely rebuilds the 'users' table to the correct schema.
    This script handles migrating data from an old schema that might have
    a 'password' column instead of or in addition to 'password_hash'.
    """
    db_path = 'database.db'
    print(f"Connecting to database at {db_path} to rebuild 'users' table...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Get existing table info
        cursor.execute("PRAGMA table_info(users);")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        print(f"Found columns in 'users' table: {list(columns.keys())}")

        # 2. Create the new, correct table
        print("Creating 'users_new' table with correct schema...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN NOT NULL DEFAULT 0
            )
        ''')

        # 3. Figure out which columns to copy from the old table
        if 'username' not in columns:
            print("CRITICAL ERROR: 'users' table has no 'username' column. Aborting.", file=sys.stderr)
            conn.rollback()
            return

        select_columns = ["id", "username"]
        insert_columns = ["id", "username"]
        
        # Prefer new password_hash, fall back to old password
        if 'password_hash' in columns:
            select_columns.append("password_hash")
            insert_columns.append("password_hash")
            print("Migrating existing 'password_hash' column.")
        elif 'password' in columns:
            select_columns.append("password")  # Select the old 'password' column
            insert_columns.append("password_hash") # But insert it into the new 'password_hash'
            print("Found old 'password' column, will migrate its data to 'password_hash'.")
        else:
            print("WARNING: No 'password' or 'password_hash' column found. New 'password_hash' will be empty.", file=sys.stderr)
            select_columns.append("''") # Add empty string to satisfy NOT NULL
            insert_columns.append("password_hash")

        if 'is_admin' in columns:
            select_columns.append("is_admin")
            insert_columns.append("is_admin")
            print("Migrating existing 'is_admin' column.")
        else:
            print("No 'is_admin' column found. Defaulting users to non-admin.")
            select_columns.append("0") # Default to 0
            insert_columns.append("is_admin")

        # 4. Copy data from old table to new table
        select_cols_str = ", ".join(select_columns)
        insert_cols_str = ", ".join(insert_columns)
        
        print(f"Copying data from 'users' to 'users_new'...")
        
        try:
            cursor.execute(f"INSERT INTO users_new ({insert_cols_str}) SELECT {select_cols_str} FROM users;")
        except Exception as e:
            print(f"CRITICAL: Failed to copy data. {e}", file=sys.stderr)
            print("Your database might be in an inconsistent state. Rolling back.", file=sys.stderr)
            conn.rollback()
            return

        print("Data copied successfully.")

        # 5. Drop the old table
        print("Dropping old 'users' table...")
        cursor.execute("DROP TABLE users;")

        # 6. Rename the new table to the old name
        print("Renaming 'users_new' to 'users'...")
        cursor.execute("ALTER TABLE users_new RENAME TO users;")

        conn.commit()
        print("\nDatabase 'users' table has been successfully rebuilt!")
        print("You should now be able to register and log in.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        conn.rollback()
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    rebuild_users_table()
