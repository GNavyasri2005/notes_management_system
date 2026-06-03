from flask import Flask, render_template, request, redirect, session, flash, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from functools import wraps

app = Flask(__name__)

# =========================
# SECRET KEY
# =========================
app.config["SECRET_KEY"] = "myverysecretkey"

# =========================
# SESSION CONFIG
# =========================
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
Session(app)

# =========================
# MAIL CONFIG
# =========================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'navyasrigongati@gmail.com'
app.config['MAIL_PASSWORD'] = 'YOUR_APP_PASSWORD'  # 🔴 replace with real app password (no spaces)

mail = Mail(app)

# Token system
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# =========================
# DB CONNECTION
# =========================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="notes_management_system"
    )

# =========================
# LOGIN REQUIRED
# =========================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


# =========================
# HOME
# =========================
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')


# =========================
# REGISTER
# =========================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=%s OR email=%s", (username, email))
        if cur.fetchone():
            flash("User already exists", "danger")
            return redirect(url_for('register'))

        cur.execute(
            "INSERT INTO users(username,email,password) VALUES(%s,%s,%s)",
            (username, email, password)
        )

        conn.commit()
        cur.close()
        conn.close()

        flash("Registered Successfully", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


# =========================
# LOGIN (FIXED)
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # allow login with username OR email
        cur.execute(
            "SELECT * FROM users WHERE username=%s OR email=%s",
            (username_or_email, username_or_email)
        )

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user is None:
            flash("User not found", "danger")
            return redirect(url_for('login'))

        if check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Login Successful", "success")
            return redirect(url_for('dashboard'))

        flash("Wrong password", "danger")
        return redirect(url_for('login'))

    return render_template('login.html')


# =========================
# LOGOUT
# =========================
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('login'))


# =========================
# DASHBOARD
# =========================
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM notes WHERE user_id=%s ORDER BY id DESC",
                (session['user_id'],))

    notes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('dashboard.html', notes=notes)


# =========================
# ADD NOTE
# =========================
@app.route('/addnote', methods=['GET', 'POST'])
@login_required
def addnote():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO notes(title,content,user_id) VALUES(%s,%s,%s)",
            (title, content, session['user_id'])
        )

        conn.commit()
        cur.close()
        conn.close()

        flash("Note Added", "success")
        return redirect(url_for('viewnotes'))

    return render_template('addnote.html')


# =========================
# VIEW NOTES
# =========================
@app.route('/viewnotes')
@login_required
def viewnotes():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM notes WHERE user_id=%s ORDER BY id DESC",
                (session['user_id'],))

    notes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('viewnotes.html', notes=notes)


# =========================
# SEARCH NOTES
# =========================
@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if query:
        cur.execute("""
            SELECT * FROM notes 
            WHERE user_id=%s 
            AND (title LIKE %s OR content LIKE %s)
            ORDER BY id DESC
        """, (session['user_id'], f"%{query}%", f"%{query}%"))
    else:
        cur.execute("SELECT * FROM notes WHERE user_id=%s ORDER BY id DESC",
                    (session['user_id'],))

    notes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('viewnotes.html', notes=notes, search_query=query)


# =========================
# UPDATE NOTE
# =========================
@app.route('/updatenote/<int:note_id>', methods=['GET', 'POST'])
@login_required
def updatenote(note_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM notes WHERE id=%s AND user_id=%s",
                (note_id, session['user_id']))
    note = cur.fetchone()

    if not note:
        flash("Note not found", "danger")
        return redirect(url_for('viewnotes'))

    if request.method == 'POST':
        cur.execute("""
            UPDATE notes 
            SET title=%s, content=%s 
            WHERE id=%s AND user_id=%s
        """, (request.form['title'], request.form['content'], note_id, session['user_id']))

        conn.commit()
        cur.close()
        conn.close()

        flash("Note Updated", "success")
        return redirect(url_for('viewnotes'))

    cur.close()
    conn.close()

    return render_template('updatenote.html', note=note)


# =========================
# DELETE NOTE
# =========================
@app.route('/deletenote/<int:note_id>', methods=['POST'])
@login_required
def deletenote(note_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM notes WHERE id=%s AND user_id=%s",
                (note_id, session['user_id']))

    conn.commit()
    cur.close()
    conn.close()

    flash("Note Deleted", "info")
    return redirect(url_for('viewnotes'))


# =========================
# ABOUT
# =========================
@app.route('/about')
def about():
    return render_template('about.html')


# =========================
# CONTACT
# =========================
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash("Message sent successfully!", "success")
        return redirect(url_for('contact'))

    return render_template('contact.html')


# =========================
# FORGOT PASSWORD
# =========================
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            token = s.dumps(email, salt='password-reset-salt')
            reset_link = url_for('reset_password', token=token, _external=True)

            msg = Message(
                "Password Reset Request",
                sender=app.config['MAIL_USERNAME'],
                recipients=[email]
            )

            msg.body = f"Click to reset password:\n{reset_link}\nLink expires in 15 min."

            try:
                mail.send(msg)
            except Exception as e:
                print("Mail error:", e)

        flash("If email exists, reset link sent!", "info")
        return redirect(url_for('login'))

    return render_template('forgot_password.html')


# =========================
# RESET PASSWORD
# =========================
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=900)
    except:
        flash("Link expired or invalid", "danger")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("UPDATE users SET password=%s WHERE email=%s", (new_password, email))

        conn.commit()
        cur.close()
        conn.close()

        flash("Password updated successfully!", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

# =========================
# search
# =========================


@app.route('/search-user', methods=['GET'])
@login_required
def search_user():
    username = request.args.get('username', '').strip()

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # find user
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone()

    if not user:
        flash("User not found", "danger")
        return redirect(url_for('dashboard'))

    # get notes of that user
    cur.execute("SELECT * FROM notes WHERE user_id=%s ORDER BY id DESC", (user['id'],))
    notes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('viewnotes.html', notes=notes, search_user=username)


# =========================
# RUN APP
# =========================
if __name__ == '__main__':
    app.run(debug=True)