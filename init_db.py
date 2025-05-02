import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    github TEXT,
    linkedin TEXT,
    twitter TEXT,
    portfolio TEXT
)
''')

conn.commit()
conn.close()

print("✅ Database initialized.")
