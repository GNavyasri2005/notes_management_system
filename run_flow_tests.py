from app import app, get_db_connection, s
from werkzeug.security import check_password_hash

client = app.test_client()

# Unique test user
username = 'flowtest'
email = 'flowtest@example.com'
password = 'InitialPass123'
new_password = 'NewPass456'

# Clean up existing test user
conn = get_db_connection()
cur = conn.cursor()
cur.execute('DELETE FROM users WHERE email=? OR username=?', (email, username))
conn.commit()
cur.close(); conn.close()

# 1) Register
resp = client.post('/register', data={'username': username, 'email': email, 'password': password}, follow_redirects=False)
print('Register status:', resp.status_code, resp.headers.get('Location'))

# 2) Register duplicate
resp2 = client.post('/register', data={'username': username, 'email': email, 'password': password}, follow_redirects=False)
print('Duplicate register status:', resp2.status_code, resp2.headers.get('Location'))

# 3) Login with initial password
resp3 = client.post('/login', data={'username': username, 'password': password}, follow_redirects=False)
print('Login status:', resp3.status_code, resp3.headers.get('Location'))

# 4) Create reset token and POST to reset-password
token = s.dumps(email, salt='password-reset-salt')
resp4 = client.post(f'/reset-password/{token}', data={'password': new_password, 'confirm_password': new_password}, follow_redirects=False)
print('Reset post status:', resp4.status_code, resp4.headers.get('Location'))

# 5) Login with new password
resp5 = client.post('/login', data={'username': username, 'password': new_password}, follow_redirects=False)
print('Login with new pass status:', resp5.status_code, resp5.headers.get('Location'))

# 6) Check DB stored password
conn = get_db_connection()
cur = conn.cursor()
cur.execute('SELECT password FROM users WHERE email=?', (email,))
row = cur.fetchone()
print('Stored password row:', row)
if row:
    stored = row[0]
    print('Stored is hashed?:', stored.startswith('scrypt:') or stored.startswith('pbkdf2:') or stored.startswith('argon2:'))
    print('check_password_hash(new):', check_password_hash(stored, new_password))
cur.close(); conn.close()
