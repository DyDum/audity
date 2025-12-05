import sqlite3
conn = sqlite3.connect('./cis_benchmarks.db')
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    content TEXT NOT NULL,
    os_type TEXT NOT NULL DEFAULT 'any',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by_id INTEGER NOT NULL,
    created_at TEXT,
    updated_at TEXT
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS script_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL,
    server_id INTEGER NOT NULL,
    run_by_id INTEGER NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    status TEXT,
    output TEXT
);
""")
conn.commit()
conn.close()