import sqlite3
import mysql.connector

MYSQL_CONFIG = dict(host='localhost', user='root', password='root', database='notes_management_system')
SQLITE_DB = 'notes.db'

def create_sqlite_tables(conn):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            email TEXT,
            password TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY,
            title TEXT,
            content TEXT,
            user_id INTEGER,
            created_at TEXT
        )
    ''')
    conn.commit()

def migrate():
    try:
        mconn = mysql.connector.connect(**MYSQL_CONFIG)
    except Exception as e:
        print('Could not connect to MySQL:', e)
        return

    mcur = mconn.cursor(dictionary=True)

    # fetch users
    mcur.execute('SELECT id, username, email, password FROM users')
    users = mcur.fetchall()

    # fetch notes
    # try to handle different column sets
    try:
        mcur.execute('SELECT id, title, content, user_id, created_at FROM notes')
        notes = mcur.fetchall()
    except Exception:
        mcur.execute('SELECT id, title, content, user_id FROM notes')
        rows = mcur.fetchall()
        notes = []
        for r in rows:
            r['created_at'] = None
            notes.append(r)

    mcur.close()
    mconn.close()

    sconn = sqlite3.connect(SQLITE_DB)
    sconn.row_factory = sqlite3.Row
    create_sqlite_tables(sconn)
    # ensure notes table has created_at column (older DBs may lack it)
    curinfo = sconn.execute("PRAGMA table_info('notes')").fetchall()
    cols = [c[1] for c in curinfo]
    if 'created_at' not in cols:
        sconn.execute("ALTER TABLE notes ADD COLUMN created_at TEXT")
        sconn.commit()
    scur = sconn.cursor()

    # optional: clear existing data to avoid duplicates
    scur.execute('DELETE FROM users')
    scur.execute('DELETE FROM notes')
    sconn.commit()

    for u in users:
        scur.execute('INSERT OR REPLACE INTO users(id, username, email, password) VALUES(?,?,?,?)',
                     (u['id'], u.get('username'), u.get('email'), u.get('password')))

    for n in notes:
        scur.execute('INSERT OR REPLACE INTO notes(id, title, content, user_id, created_at) VALUES(?,?,?,?,?)',
                     (n.get('id'), n.get('title'), n.get('content'), n.get('user_id'), n.get('created_at')))

    sconn.commit()
    scur.close()
    sconn.close()

    print(f'Migrated {len(users)} users and {len(notes)} notes into {SQLITE_DB}')

if __name__ == '__main__':
    migrate()
