import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()
try:
    c.execute("ALTER TABLE users ADD COLUMN profile_pic TEXT")
    print("✅ profile_pic column added.")
except sqlite3.OperationalError:
    print("profile_pic column already exists or migration failed.")
conn.commit()
conn.close() 