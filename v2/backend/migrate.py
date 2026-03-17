import sqlite3, os, sys

db = "advising_v2.db"
if not os.path.exists(db):
    print("DB not found at", os.path.abspath(db))
    sys.exit(1)

con = sqlite3.connect(db)
cur = con.cursor()

cur.execute("PRAGMA table_info(majors)")
existing = {row[1] for row in cur.fetchall()}
print("Existing majors columns:", existing)

for col, defn in [
    ("assignment_types", 'TEXT DEFAULT \'["S.C.E", "F.E.C"]\''),
    ("rules_updated_at", "DATETIME"),
]:
    if col not in existing:
        cur.execute(f"ALTER TABLE majors ADD COLUMN {col} {defn}")
        print(f"  Added column: {col}")
    else:
        print(f"  Already exists: {col}")

cur.executescript("""
CREATE TABLE IF NOT EXISTS course_equivalents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_id INTEGER NOT NULL REFERENCES majors(id),
    alias_code TEXT NOT NULL,
    canonical_code TEXT NOT NULL,
    UNIQUE(major_id, alias_code)
);

CREATE TABLE IF NOT EXISTS course_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_id INTEGER NOT NULL REFERENCES majors(id),
    course_code TEXT NOT NULL,
    credits REAL,
    passing_grades TEXT,
    course_type TEXT,
    from_semester TEXT,
    to_semester TEXT
);

CREATE TABLE IF NOT EXISTS course_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_id INTEGER NOT NULL REFERENCES majors(id),
    student_id TEXT NOT NULL,
    assignment_type TEXT NOT NULL,
    course_code TEXT NOT NULL,
    UNIQUE(major_id, student_id, assignment_type)
);
""")

con.commit()
con.close()
print("Migration complete.")
