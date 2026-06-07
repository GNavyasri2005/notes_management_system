import sqlite3
from werkzeug.security import generate_password_hash

DB = 'notes.db'

HASH_PREFIXES = ('scrypt:', 'pbkdf2:', 'argon2:')

def is_hashed(pw):
    if not pw:
        return False
    return any(pw.startswith(pref) for pref in HASH_PREFIXES)

def migrate():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        cur.execute('SELECT id, username, email, password FROM users')
    except Exception as e:
        print('ERROR: could not read users table:', e)
        cur.close()
        conn.close()
        return

    rows = cur.fetchall()
    if not rows:
        print('No users found; nothing to do.')
        cur.close()
        conn.close()
        return

    updated = 0
    total = 0
    for r in rows:
        total += 1
        pw = r['password']
        if not is_hashed(pw):
            new_hash = generate_password_hash(pw)
            cur.execute('UPDATE users SET password=? WHERE id=?', (new_hash, r['id']))
            updated += 1
            print(f"Updated user id={r['id']} username={r['username']}")

    conn.commit()
    cur.close()
    conn.close()

    print(f"Migration complete: {updated} of {total} users updated to hashed passwords.")

if __name__ == '__main__':
    migrate()
