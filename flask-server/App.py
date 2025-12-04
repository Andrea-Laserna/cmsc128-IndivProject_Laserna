from ast import If
from flask import Flask, flash, render_template, request, redirect, url_for, session, make_response
from datetime import datetime
from dotenv import load_dotenv
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from functools import wraps

# load variables from .env
load_dotenv()

app = Flask(__name__)
# if key doesnt exist from .env, use dev_secret_key instead
app.secret_key = os.getenv("SECRET_KEY") or "dev_secret_key"

# generate and verify secure tokens 
# use the secret key to cryptographically sign my tokens so nobody can forge them
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
            list_id INTEGER,
            is_deleted BIT DEFAULT 0,
            FOREIGN KEY (list_id) REFERENCES lists (list_id)
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lists (
            list_id INTEGER PRIMARY KEY AUTOINCREMENT,
            list_name TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users (user_id) 
        )       
    ''')
    cursor.execute('''
       CREATE TABLE IF NOT EXISTS list_collaborators (
            list_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (list_id, user_id),
            FOREIGN KEY (list_id) REFERENCES lists (list_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )             
    ''')
    conn.commit()
    conn.close()

# prevent caching for ALL responses
@app.after_request
def add_header(response):
    # This ensures that the response is treated as a proper Response object 
    # before we try to set headers
    response = make_response(response) 
    
    # Set headers to prevent caching by the browser
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

# helper functions

# retrieve all tasks with default sorting option
def get_tasks(list_id, sort="created_at", order="desc"):
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

    # check if user is owner of collaborator
    cursor.execute('''
        SELECT 1 FROM lists
        WHERE list_id = ? AND owner_id = ?

        UNION
                   
        SELECT 1 FROM list_collaborators
        WHERE list_id = ? AND user_id = ?
    ''', (list_id, user_id, list_id, user_id))

    if not cursor.fetchone():
        conn.close()
        raise PermissionError("You do not have access to this list.")

    if sort == "priority":
        cursor.execute('''
            SELECT * FROM tasks 
                WHERE list_id = ? AND is_deleted = 0
                ORDER BY CASE priority 
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END ASC
            ''', (list_id,))
    else:
        cursor.execute(f'SELECT * FROM tasks WHERE list_id = ? AND is_deleted = 0 ORDER BY {sort} {order.upper()}', (list_id,))

    tasks = cursor.fetchall()
    cursor.close()
    return tasks

# add a task
def add_task(task_name, priority, deadline, list_id):
    conn = sqlite3.connect(DB_path)
    # enable foreign key enforcement
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (task_name, priority, deadline, list_id) VALUES(?, ?, ?, ?)', (task_name, priority, deadline, list_id))
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
    # encryot password before saving to database
    hashwed_pwd = generate_password_hash(password)
    cursor.execute('INSERT INTO users (name, password, email) VALUES(?, ?, ?)', (name, hashwed_pwd, email))

    # get newly created user_id
    user_id = cursor.lastrowid
    # create default list
    cursor.execute('INSERT INTO lists (list_name, owner_id) VALUES(?, ?)', ("My Dooby List", user_id))

    conn.commit()
    cursor.close()
    conn.close()

    return user_id

def get_default_list_id(user_id):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    # fetch the first list created by the user (default list)
    cursor.execute('SELECT list_id FROM lists WHERE owner_id=? ORDER BY list_id ASC LIMIT 1', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

# retrieve all details
def get_user(name):
    conn = sqlite3.connect(DB_path)
    conn.row_factory = sqlite3.Row  # return dict-like rows
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, email, password FROM users WHERE name=?", (name,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_email(email):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, email, password FROM users WHERE email=?", (email,))
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

def get_collaborators(list_id):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.user_id, u.name, u.email
        FROM list_collaborators lc
        JOIN users u ON lc.user_id = u.user_id
        WHERE lc.list_id = ?
    ''', (list_id,))
    collaborators = cursor.fetchall()
    conn.close()
    return collaborators

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

    # get list id from url query string /?list_id=7
    list_id = request.args.get("list_id")
    if list_id:
        try:
            # since URL parameters are strings, convert to integer
            list_id = int(list_id)
        except ValueError:
            flash("Invalid list selected.")
            return redirect(url_for('index'))  # safer to redirect to a create list page
    else:
        list_id = get_default_list_id(user_id)

    # if get_default_list_id returned None (user has no lists)
    if not list_id:
        flash("No list available. Please create a list first.")
        # send the other variables to index.html
        return render_template("index.html", tasks=[], lists=[], current_list_id=None, name=session['name'], email=session['email'])

    # fetch tasks of that list
    try:
        tasks = get_tasks(list_id, sort, order)
    except PermissionError:
        flash("You do not have access to this list.")
        tasks = []  # show empty tasks instead of redirecting


    # fetch all owned and collaborated lists
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.list_id, l.list_name, u.name AS owner_name
        FROM lists l
        JOIN users u ON l.owner_id = u.user_id
        LEFT JOIN list_collaborators lc ON l.list_id = lc.list_id
        WHERE l.owner_id = ? OR lc.user_id = ?
    ''', (user_id, user_id))

    lists = cursor.fetchall()
    conn.close()

    # pass the session values explicitly from login details
    return render_template("index.html", tasks=tasks, lists=lists, current_list_id=int(list_id), name=session['name'], email=session['email'])

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

    # get list_id from form
    list_id = request.form.get('list_id')
    # if form did not include list_id
    if not list_id:
        # fall back to default
        list_id = get_default_list_id(user_id)

    # if get default list returns None
    if not list_id:
        flash("No list available to add the task.")
        return redirect(url_for('index'))

    # check if user has access to list: owner or collaborator
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM lists
        WHERE list_id = ? AND owner_id = ?
        UNION
        SELECT 1 FROM list_collaborators
        WHERE list_id = ? AND user_id = ?
    ''', (list_id, user_id, list_id, user_id))

    if not cursor.fetchone(): # if row empty
        conn.close()
        flash("You do not have access to this list.")
        return redirect(url_for('index'))

    conn.close()

    # add the task
    try:
        add_task(task_name, priority, deadline, list_id)
        flash("Task addded successfully!")
    except sqlite3.IntegrityError:
        flash("Login to add task.")
        return redirect(url_for('login'))
    # remain in the same list page
    return redirect(url_for('index', list_id=list_id)) 

# edit tasks
@app.route('/update_task/<int:task_id>', methods=['POST'])
def edit_task_route(task_id):
    user_id = session['user_id']
    task_name = request.form['task_name']
    priority = request.form['priority']
    deadline = request.form['deadline']

    # get hidden list_id from form
    list_id = request.form.get('list_id')
    if list_id:
        list_id = int(list_id)
    else:
        # fallback: fetch list_id from the task itself
        conn = sqlite3.connect(DB_path)
        cursor = conn.cursor()
        cursor.execute('SELECT list_id FROM tasks WHERE task_id=?', (task_id,))
        row = cursor.fetchone()
        conn.close()
        # if match, convert
        if row:
            list_id = row[0]
        # if no match in db, fall back to default list_id
        else:
            list_id = get_default_list_id(user_id)

    edit_task(task_id, task_name, priority, deadline)
    return redirect(url_for('index', list_id=list_id))

# delete tasks
@app.route('/delete_task/<int:task_id>', methods=['GET']) 
def delete_task_route(task_id):
    # fetch the list_id of this task
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('SELECT list_id FROM tasks WHERE task_id=?', (task_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        flash("Task not found.", "error")
        return redirect(url_for('index')) # fall back to default
    
    list_id = row[0]
    conn.close()

    delete_task(task_id)
    flash(f"Task deleted! <a href='{url_for('undo_task_delete_route', task_id=task_id)}' class='btn undo-btn'>Undo</a>", "undo")

    return redirect(url_for('index', list_id=list_id)) 

# toggle tasks
@app.route('/toggle_task/<int:task_id>', methods=['POST'])
def toggle_task_route(task_id):
    isChecked = int(request.form['isChecked'])
    toggle_task(task_id, isChecked)
    return '', 204 # no content

# undo task delete
@app.route('/undo_task_delete/<int:task_id>', methods=['GET', 'POST'])
def undo_task_delete_route(task_id):
    # fetch the list_id of this task
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('SELECT list_id FROM tasks WHERE task_id=?', (task_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        flash("Task not found.", "error")
        return redirect(url_for('index')) # fall back to default
    
    list_id = row[0]
    conn.close()
    
    undo_task_delete(task_id)

    return redirect(url_for('index', list_id=list_id)) 

# sign up page
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        # Request the following from the form to add to database
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']

        # If user is already taken, signup again
        if user_exists(name, email):
            flash("Username or email already taken. Please try again.")
            return redirect(url_for('signup'))
        else: 

            signup_user(name, password, email)
            flash("Account created successfully!")
            # Proceed to login page after signup
            return redirect(url_for('login')) 
    # Load signup page first before processing form 
    return render_template("signup.html")

# login page
@app.route('/login', methods=['POST', 'GET'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        # user submitted the form
        name = request.form['name']
        password = request.form['password']
        # verify credentials - only get the unique name because we dont need the email anymore
        user = get_user(name)
        # if user doesnt exist in the db, login again
        if user is None:
            flash('Username not found.')
            return redirect(url_for('login'))
        
        # if user exists, retrieve hashed pw from db
        stored_pwd = user['password']

        # verify password
        # rehash entered password and compare to the stored password
        if check_password_hash(stored_pwd, password):
            # store session details from get_user(name) signed by secret key
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            session['email'] = user['email']
            flash('Login successful!')
            return redirect(url_for('index')) 
        else:
            flash('Incorrect password.')
            return redirect(url_for('login'))
    # visit login page first
    return render_template("login.html")

# forgot password
@app.route('/forgot_password', methods = ['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = get_user_email(email)

        if user:
            # generate token from user email
            token = serializer.dumps(email, salt='password-recovery')
            # generate link with token
            # reset_password will handle the request
            reset_link = url_for('reset_password', token=token, _external=True)

            # show link on page instead of sending email
            return redirect(url_for('show_reset_link', link=reset_link))
        else:
            # ask for password again
            flash("Email not found.")
            return redirect(url_for('forgot_password'))
    # load forgotpwd page first
    return render_template('forgotpwd.html')

# reset link
@app.route('/show_reset_link')
def show_reset_link():
    # retrieve reset_link from /forgot_password
    link = request.args.get('link')
    # pass the link to template to display
    return render_template('resetlink.html', link=link)

# reset password
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
# token comes from the reset link
def reset_password(token):
    # step 1
    try:
        # decode token back to original email
        # salt to ensure it only works for password recovery tokens
        email = serializer.loads(token, salt='password-recovery', max_age=3600)
    except (SignatureExpired, BadSignature):
        '''
        SignatureExpired - token is valid but expired
        BadSignature - token was tampered with or invalid
        '''
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        # once the user has submitted their new password
        new_password = request.form['new_password']
        hashed = generate_password_hash(new_password)

        conn = sqlite3.connect(DB_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password=? WHERE email=?", (hashed, email))
        conn.commit()
        conn.close()

        flash("Password reset successful!", "success")
        return redirect(url_for('login'))

    # step 2: show the reset form 
    return render_template('resetpass.html', email=email)
    
# profile
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # step 1
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    user_id = session.get('user_id')

    if not user_id:
        flash("You need to log in to access your profile.", "error")
        return redirect(url_for('login'))

    # step 3
    if request.method == 'POST':
        # using get for flexibility - will return none if user did not input anything instead of raising an error 
        name = request.form.get('name')
        new_email = request.form.get('email')
        password = request.form.get('password')

        updates = [] # list of attributes to update
        params = [] # list of parameters to replace the value in the query

        if name:
            updates.append("name=?")
            params.append(name)
            session['name'] = name

        if new_email:
            updates.append("email=?")
            params.append(new_email)
            session['email'] = new_email

        if password and password.strip(): # using strip to remove trailing white spaces
            hashed = generate_password_hash(password)
            updates.append("password=?")
            params.append(hashed)

        if updates:
            sql = f"UPDATE users SET {', '.join(updates)} WHERE user_id=?"
            params.append(user_id)
            cursor.execute(sql, tuple(params)) 
            conn.commit()
            flash("Profile updated successfully!", "success")
        else:
            flash("No changes detected.", "info")

        return redirect(url_for('index'))

    # step 2 : GET request - prefill form
    cursor.execute("SELECT name, email FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template('profile.html', user=user)


# === COLLABORATION ===

# create list
@app.route('/create_list', methods=['POST'])
def create_list():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))

    # '' - default value if list name not found
    list_name = request.form.get('list_name', '').strip()
    if not list_name:
        flash("List name cannot be empty.", "error")
        return redirect(url_for('collaboration'))

    user_id = session['user_id']

    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO lists (list_name, owner_id) VALUES (?, ?)', (list_name, user_id))
    conn.commit()
    conn.close()

    flash(f"List '{list_name}' created successfully!", "success")
    return redirect(url_for('collaboration'))

# collaboration
@app.route('/collaboration')
def collaboration():
    if 'user_id' not in session:
        flash("Please login to view your lists.")
        return redirect(url_for('login'))

    user_id = session['user_id']

    # read list_id from url
    current_list_id = request.args.get('list_id')
    if current_list_id:
        try:
            current_list_id = int(current_list_id)
        except ValueError:
            current_list_id = None

    # fetch all owned and collaborated lists
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.list_id, l.list_name, u.name AS owner_name
        FROM lists l
        JOIN users u ON l.owner_id = u.user_id
        LEFT JOIN list_collaborators lc ON l.list_id = lc.list_id
        WHERE l.owner_id = ? OR lc.user_id = ?
        GROUP BY l.list_id
        ORDER BY l.list_id ASC
    ''', (user_id, user_id))
    lists = cursor.fetchall()
    conn.close()

    return render_template('collaboration.html', lists=lists, current_list_id=current_list_id, get_collaborators=get_collaborators)


@app.route('/add_collaborator', methods=['POST'])
def add_collaborator():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']
    list_id = int(request.form['list_id'])
    collaborator_email = request.form['collaborator_email']

    # verify if the current user owns the list
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('SELECT owner_id FROM lists WHERE list_id=?', (list_id,))
    owner = cursor.fetchone()
    if not owner or owner[0] != user_id:
        flash("You do not have permission to add collaborators.", "error")
        conn.close()
        return redirect(url_for('index', list_id=list_id))

    # find the collaborator user_id by email
    cursor.execute('SELECT user_id FROM users WHERE email=?', (collaborator_email,))
    collaborator = cursor.fetchone()
    if not collaborator:
        flash("User not found.", "error")
        conn.close()
        return redirect(url_for('index', list_id=list_id))

    collaborator_id = collaborator[0]

    # prevent adding self
    if collaborator_id == user_id:
        flash("You cannot add yourself as collaborator.", "info")
        conn.close()
        return redirect(url_for('index', list_id=list_id))

    # add collaborator if not already exists
    try:
        cursor.execute('INSERT INTO list_collaborators (list_id, user_id) VALUES (?, ?)', (list_id, collaborator_id))
        conn.commit()
        flash(f"Added collaborator: {collaborator_email}", "success")
    except sqlite3.IntegrityError:
        flash("User is already a collaborator.", "info")

    conn.close()
    return redirect(url_for('index', list_id=list_id))

@app.route('/remove_collaborator', methods=['POST'])
def remove_collaborator():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']
    list_id = int(request.form['list_id'])
    collaborator_id = int(request.form['collaborator_id'])

    # verify if the current user owns the list
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('SELECT owner_id FROM lists WHERE list_id=?', (list_id,))
    owner = cursor.fetchone()
    if not owner or owner[0] != user_id:
        flash("You do not have permission to remove collaborators.", "error")
        conn.close()
        return redirect(url_for('index', list_id=list_id))

    # remove collaborator
    cursor.execute('DELETE FROM list_collaborators WHERE list_id=? AND user_id=?', (list_id, collaborator_id))
    conn.commit()
    conn.close()
    flash("Collaborator removed successfully.", "success")
    return redirect(url_for('index', list_id=list_id))

# logout
@app.route('/logout')
def logout():
    session.clear()  # removes user_id, username, etc.
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# run
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
   


