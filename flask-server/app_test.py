from flask import Flask, flash, render_template, request, redirect, url_for, session
from datetime import datetime
from dotenv import load_dotenv
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# load variables from .env
load_dotenv()

app = Flask(__name__)

'''
if key doesnt exist from .env, use dev_secret_key instead
flask gives users a cookie to remember (e.g. session = {"user_id": 42})
since flask stores it as plain text, it can be changed by another user so before sending
the session cookie to the user's browser, flask runs it through a cryptographic signing algorithm
using the secret key
'''
app.secret_key = os.getenv("SECRET_KEY") or "dev_secret_key"

# generate and verify secure tokens 
serializer = URLSafeTimedSerializer(app.secret_key) 

DB_path = 'tasks.db'

# creating the table
def init_db():
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor() # allows python to speak to sqlite
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY,
            task_name TEXT NOT NULL,
            isChecked BIT DEFAULT 0,
            priority TEXT NOT NULL,
            deadline DATETIME NOT NULL,
            created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
            is_deleted BIT DEFAULT 0,
            uid INTEGER,
            FOREIGN KEY (uid) REFERENCES users (user_id)
        )               
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL   
        )
    ''')
    conn.commit()
    conn.close()

# helper functions

# retrieve all tasks with default sorting option
def get_tasks(sort="created_at", order="desc"):
    user_id = session['user_id']

    # security purposes lol
    allowed_sorts = {"priority", "created_at", "deadline"}
    allowed_order = {"asc", "desc"}

    if sort not in allowed_sorts:
        sort = "created_at"
    if order not in allowed_order:
        order = "desc"

    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()

    if sort == "priority":
        cursor.execute('''
            SELECT * FROM tasks 
                WHERE uid = ? AND is_deleted = 0
                ORDER BY CASE priority 
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END ASC
            ''', (user_id,))
    else:
        cursor.execute(f'SELECT * FROM tasks WHERE uid = ? AND is_deleted = 0 ORDER BY {sort} {order.upper()}', (user_id,))

    tasks = cursor.fetchall()
    cursor.close()
    return tasks

# add a task
def add_task(task_name, priority, deadline, user_id):
    conn = sqlite3.connect(DB_path)
    # enable foreign key enforcement
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (task_name, priority, deadline, uid) VALUES(?, ?, ?, ?)', (task_name, priority, deadline, user_id))
    conn.commit()
    cursor.close()
    conn.close()

# edit task
def edit_task(task_id, task_name, priority, deadline):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET task_name = ?, priority = ?, deadline = ? WHERE task_id = ?', (task_name, priority, deadline, task_id))
    conn.commit()
    cursor.close()
    conn.close()

# delete task
def delete_task(task_id):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET is_deleted = 1 WHERE task_id = ?', (task_id,))
    conn.commit()
    cursor.close()
    conn.close()

# toggle task checkbox
def toggle_task(task_id, isChecked):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET isChecked = ? WHERE task_id = ?', (isChecked, task_id))
    conn.commit()
    cursor.close()
    conn.close()

# undo delete task
def undo_task_delete(task_id):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET is_deleted = 0 WHERE task_id = ?', (task_id,))
    conn.commit()
    cursor.close()
    conn.close()

# sign up user
def signup_user(name, password, email):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    hashwed_pwd = generate_password_hash(password)
    cursor.execute('INSERT INTO users (name, password, email) VALUES(?, ?, ?)', (name, hashwed_pwd, email))
    conn.commit()
    cursor.close()
    conn.close()

# login user
def get_user(name):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE name = ?', (name,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def get_user_email(email):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# check if name or email already exists
def user_exists(name, email):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ? OR email = ?", (name, email))
    user = cursor.fetchone()
    conn.close()
    return user

# flask connections

# home page
@app.route('/')
def index():
    # check if session contains user id
    if 'user_id' not in session:
        flash("Please login to add tasks.")
        return redirect(url_for('login'))

    user_id = session['user_id']

    sort = request.args.get("sort", "created_at")
    order = request.args.get("order", "desc")
    tasks = get_tasks(sort, order) # includes sorting and order option

    # get user info
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, email FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("index.html", tasks=tasks, user = user)

# adding tasks
@app.route('/add_task', methods=['POST'])
def add_task_route():
    # check if session contains user id
    if 'user_id' not in session:
        flash("Please login to add tasks.")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    task_name = request.form['task_name']
    priority = request.form['priority']
    deadline = request.form['deadline']
    try:
        add_task(task_name, priority, deadline, user_id)
    except sqlite3.IntegrityError:
        flash("Login to add task.")
        return redirect(url_for('login'))

    return redirect(url_for('index')) 

# edit tasks
@app.route('/update_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task_route(task_id):
    task_name = request.form['task_name']
    priority = request.form['priority']
    deadline = request.form['deadline']
    edit_task(task_id, task_name, priority, deadline)
    return redirect(url_for('index')) 

# delete tasks
@app.route('/delete_task/<int:task_id>', methods=['GET']) 
def delete_task_route(task_id):
    delete_task(task_id)
    # toast
    flash(f"Task deleted! <a href='{url_for('undo_task_delete_route', task_id=task_id)}' class='btn undo-btn'>Undo</a>", "undo")
    return redirect(url_for('index'))

# toggle tasks
@app.route('/toggle_task/<int:task_id>', methods=['POST'])
def toggle_task_route(task_id):
    isChecked = int(request.form['isChecked'])
    toggle_task(task_id, isChecked)
    return '', 204 # no content

# undo task delete
@app.route('/undo_task_delete/<int:task_id>', methods=['GET', 'POST'])
def undo_task_delete_route(task_id):
    undo_task_delete(task_id)
    return redirect(url_for('index')) 

# sign up page
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']

        if user_exists(name, email):
            flash("Username or email already taken. Please try again.")
            return redirect(url_for('signup'))
        else: 
            signup_user(name, password, email)
            flash("Account created successfully!")
            return redirect(url_for('login')) 
            
    return render_template("signup.html")

# login page
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        # user submitted the form
        name = request.form['name']
        password = request.form['password']
        # verify credentials
        user = get_user(name)
        # check if user exists
        if user is None:
            flash('Username not found.')
            return redirect(url_for('login'))
        
        stored_pwd = user[2]

        # verify password
        if check_password_hash(stored_pwd, password):
            # store user id
            session['user_id'] = user[0]
            # display name
            session['name'] = user[1]
            flash('Login successful!')
            return redirect(url_for('index')) 
        else:
            flash('Incorrect password.')
            return redirect(url_for('login'))
    # visit login page
    return render_template("login.html")

# forgot password
@app.route('/forgot_password', methods = ['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = get_user_email(email)

        if user:
            # generate token
            token = serializer.dumps(email, salt='password-recovery')
            reset_link = url_for('reset_password', token=token, _external=True)

            # show link on page instead of sending email
            return redirect(url_for('show_reset_link', link=reset_link))
        else:
            flash("Email not found.")
            return redirect(url_for('forgot_password'))
    return render_template('forgotpwd.html')

@app.route('/show_reset_link')
def show_reset_link():
    link = request.args.get('link')
    return render_template('resetlink.html', link=link)


@app.route('/profile', methods=['GET', 'POST'])
@app.route('/profile/<token>', methods=['GET', 'POST'])
def profile(token=None):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()

    user_id = session.get('user_id')
    email = None

    # If a reset token is present, verify it
    if token:
        try:
            email = serializer.loads(token, salt='password-recovery', max_age=3600)
        except (SignatureExpired, BadSignature):
            flash("Invalid or expired reset link.", "error")
            return redirect(url_for('forgot_password'))

    # ---------------- POST: update logic ----------------
    if request.method == 'POST':
        name = request.form.get('name')
        new_email = request.form.get('email')
        password = request.form.get('password')

        # Password required if token mode, optional if logged in
        if token and not password:
            flash("Please enter a new password.", "error")
            return redirect(request.url)

        # Case 1: Logged-in profile update
        if user_id:
            if not name or not new_email:
                flash("Name and email are required.", "error")
                return redirect(url_for('profile'))

            if password.strip():
                hashed = generate_password_hash(password)
                cursor.execute("""
                    UPDATE users SET name=?, email=?, password=? WHERE user_id=?
                """, (name, new_email, hashed, user_id))
            else:
                cursor.execute("""
                    UPDATE users SET name=?, email=? WHERE user_id=?
                """, (name, new_email, user_id))

            conn.commit()
            flash("Profile updated successfully!", "success")
            session['username'] = name
            return redirect(url_for('index'))

        # Case 2: Token-based password reset
        elif email:
            hashed = generate_password_hash(password)
            cursor.execute("UPDATE users SET password=? WHERE email=?", (hashed, email))
            conn.commit()
            flash("Password reset successful!", "success")
            return redirect(url_for('login'))

        else:
            flash("Unauthorized request.", "error")
            return redirect(url_for('login'))

    # ---------------- GET: load user data ----------------
    if user_id:
        cursor.execute("SELECT name, email FROM users WHERE user_id=?", (user_id,))
        user = cursor.fetchone()
    else:
        user = ("", email or "")

    conn.close()

    # `token_mode` flag helps the template know which fields to hide/show
    return render_template('profile.html', user=user, token_mode=bool(token))

@app.route('/logout')
def logout():
    session.clear()  # removes user_id, username, etc.
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# run
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
   


