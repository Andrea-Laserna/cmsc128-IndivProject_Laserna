from flask import Flask, flash, render_template, request, redirect, url_for, session, make_response
from datetime import datetime
from dotenv import load_dotenv
import os
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

# load variables from .env
load_dotenv()

app = Flask(__name__)
# if key doesnt exist from .env, use dev_secret_key instead
app.secret_key = os.getenv("SECRET_KEY") or "dev_secret_key"

# generate and verify secure tokens 
# use the secret key to cryptographically sign my tokens so nobody can forge them
serializer = URLSafeTimedSerializer(app.secret_key)


def _ensure_sslmode(db_url: str) -> str:
    """Ensure sslmode=require is present for Supabase/Render Postgres."""
    if not db_url:
        return db_url
    # If query already present
    if "?" in db_url:
        if "sslmode=" not in db_url:
            return f"{db_url}&sslmode=require"
        return db_url
    # No query string yet
    return f"{db_url}?sslmode=require"


def _build_db_url_from_parts() -> str | None:
    """Build a SQLAlchemy Postgres URL from env parts, supporting both DB_* and lowercase keys."""
    user = os.getenv("DB_USER") or os.getenv("user")
    password = os.getenv("DB_PASSWORD") or os.getenv("password")
    host = os.getenv("DB_HOST") or os.getenv("host")
    port = os.getenv("DB_PORT") or os.getenv("port") or "5432"
    name = os.getenv("DB_NAME") or os.getenv("dbname")

    if all([user, password, host, port, name]):
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    return None


# Prefer a full DATABASE_URL (as on Render), but if it's the legacy
# 'db.supabase.co' host and we have valid parts, prefer the parts-based URL.
raw_env_url = os.getenv("DATABASE_URL")
parts_url = _build_db_url_from_parts()

chosen_url = None
if raw_env_url:
    if "db.supabase.co" in raw_env_url and parts_url:
        chosen_url = parts_url
    else:
        chosen_url = raw_env_url
elif parts_url:
    chosen_url = parts_url

DATABASE_URL = _ensure_sslmode(chosen_url) if chosen_url else None

if not DATABASE_URL:
    raise RuntimeError(
        "Database configuration missing: set DATABASE_URL or DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME (or lowercase equivalents)."
    )

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
engine_options = {"pool_pre_ping": True}
if (os.getenv("SQLALCHEMY_DISABLE_POOL", "0").lower() in ("1", "true", "yes")):
    engine_options["poolclass"] = NullPool
else:
    # Keep a small pool to respect Supabase limits when not disabling pooling
    engine_options["pool_size"] = int(os.getenv("SQLALCHEMY_POOL_SIZE", "5"))
    engine_options["max_overflow"] = int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "0"))
    engine_options["pool_recycle"] = int(os.getenv("SQLALCHEMY_POOL_RECYCLE", "300"))

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options
db = SQLAlchemy(app)

# Safe log of DB host to help diagnose env precedence (no credentials)
try:
    at_idx = DATABASE_URL.rfind("@")
    host_part = DATABASE_URL[at_idx + 1 :].split("/")[0] if at_idx != -1 else DATABASE_URL.split("//", 1)[-1].split("/")[0]
    print(f"Using database host: {host_part}")
except Exception:
    pass

# creating the table
# ================= DATABASE MODELS =================

class User(db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)

class List(db.Model):
    __tablename__ = "lists"
    list_id = db.Column(db.Integer, primary_key=True)
    list_name = db.Column(db.Text, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))

class Task(db.Model):
    __tablename__ = "tasks"
    task_id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.Text, nullable=False)
    isChecked = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Text, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    list_id = db.Column(db.Integer, db.ForeignKey("lists.list_id"))
    is_deleted = db.Column(db.Boolean, default=False)

class ListCollaborator(db.Model):
    __tablename__ = "list_collaborators"
    list_id = db.Column(db.Integer, db.ForeignKey("lists.list_id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), primary_key=True)

with app.app_context():
    db.create_all()

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

def signup_user(name, password, email):
    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()

    default_list = List(list_name="My Dooby List", owner_id=user.user_id)
    db.session.add(default_list)
    db.session.commit()
    return user.user_id


def get_user(name):
    return User.query.filter_by(name=name).first()


def get_user_email(email):
    return User.query.filter_by(email=email).first()


def user_exists(name, email):
    return User.query.filter((User.name == name) | (User.email == email)).first()


def get_default_list_id(user_id):
    lst = List.query.filter_by(owner_id=user_id).order_by(List.list_id.asc()).first()
    return lst.list_id if lst else None


def add_task(task_name, priority, deadline, list_id):
    task = Task(task_name=task_name, priority=priority, deadline=deadline, list_id=list_id)
    db.session.add(task)
    db.session.commit()


def edit_task(task_id, task_name, priority, deadline):
    t = Task.query.get(task_id)
    t.task_name = task_name
    t.priority = priority
    t.deadline = deadline
    db.session.commit()


def delete_task(task_id):
    Task.query.get(task_id).is_deleted = True
    db.session.commit()


def toggle_task(task_id, isChecked):
    Task.query.get(task_id).isChecked = bool(isChecked)
    db.session.commit()


def undo_task_delete(task_id):
    Task.query.get(task_id).is_deleted = False
    db.session.commit()


def get_tasks(list_id, sort="created_at", order="desc"):
    user_id = session["user_id"]

    owns = List.query.filter_by(list_id=list_id, owner_id=user_id).first()
    collab = ListCollaborator.query.filter_by(list_id=list_id, user_id=user_id).first()
    if not owns and not collab:
        raise PermissionError()

    q = Task.query.filter_by(list_id=list_id, is_deleted=False)

    if sort == "priority":
        q = q.order_by(db.case(
            (Task.priority == "high", 1),
            (Task.priority == "medium", 2),
            else_=3
        ))
    else:
        q = q.order_by(getattr(getattr(Task, sort), order)())

    results = q.all()
    return [
        (
            t.task_id,
            t.task_name,
            1 if t.isChecked else 0,
            t.priority,
            t.deadline,
            t.created_at,
        )
        for t in results
    ]


def get_collaborators(list_id):
    return db.session.query(User.user_id, User.name, User.email)\
        .join(ListCollaborator, ListCollaborator.user_id == User.user_id)\
        .filter(ListCollaborator.list_id == list_id)\
        .all()

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


    # fetch all owned and collaborated lists via SQLAlchemy
    lists = (
        db.session.query(
            List.list_id, List.list_name, User.name.label("owner_name")
        )
        .join(User, List.owner_id == User.user_id)
        .outerjoin(ListCollaborator, List.list_id == ListCollaborator.list_id)
        .filter((List.owner_id == user_id) | (ListCollaborator.user_id == user_id))
        .group_by(List.list_id, List.list_name, User.name)
        .order_by(List.list_id.asc())
        .all()
    )

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

    # access check via SQLAlchemy: owner or collaborator
    owns = List.query.filter_by(list_id=list_id, owner_id=user_id).first()
    collab = ListCollaborator.query.filter_by(list_id=list_id, user_id=user_id).first()
    if not owns and not collab:
        flash("You do not have access to this list.")
        return redirect(url_for('index'))

    # add the task
    add_task(task_name, priority, deadline, list_id)
    flash("Task addded successfully!")
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
        # fallback: fetch list_id from the task itself via SQLAlchemy
        t = Task.query.get(task_id)
        if t:
            list_id = t.list_id
        else:
            list_id = get_default_list_id(user_id)

    edit_task(task_id, task_name, priority, deadline)
    return redirect(url_for('index', list_id=list_id))

# delete tasks
@app.route('/delete_task/<int:task_id>', methods=['GET']) 
def delete_task_route(task_id):
    # fetch the list_id of this task via SQLAlchemy
    t = Task.query.get(task_id)
    if not t:
        flash("Task not found.", "error")
        return redirect(url_for('index')) # fall back to default
    
    list_id = t.list_id

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
    # fetch the list_id of this task via SQLAlchemy
    t = Task.query.get(task_id)
    if not t:
        flash("Task not found.", "error")
        return redirect(url_for('index')) # fall back to default
    
    list_id = t.list_id
    
    undo_task_delete(task_id)

    return redirect(url_for('index', list_id=list_id)) 

# sign up page
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    # If user already logged in, don't allow access to signup page (prevents Back showing signup)
    if 'user_id' in session:
        return redirect(url_for('index'))
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
        stored_pwd = user.password

        # verify password
        # rehash entered password and compare to the stored password
        if check_password_hash(stored_pwd, password):
            # store session details from get_user(name) signed by secret key
            session['user_id'] = user.user_id
            session['name'] = user.name
            session['email'] = user.email
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
    # If user already logged in, redirect to index (no need to recover password)
    if 'user_id' in session:
        return redirect(url_for('index'))
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
        u = User.query.filter_by(email=email).first()
        if u:
            u.password = hashed
            db.session.commit()
        flash("Password reset successful!", "success")
        return redirect(url_for('login'))

    return render_template('resetpass.html', email=email)
    
# profile
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        flash("You need to log in to access your profile.", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        new_email = request.form.get('email')
        password = request.form.get('password')

        updates = []
        if name:
            updates.append('name')
            session['name'] = name
        if new_email:
            updates.append('email')
            session['email'] = new_email
        if password and password.strip():
            updates.append('password')
            hashed = generate_password_hash(password)
        else:
            hashed = None

        if updates:
            u = User.query.get(user_id)
            if u:
                if 'name' in updates:
                    u.name = name
                if 'email' in updates:
                    u.email = new_email
                if 'password' in updates and hashed:
                    u.password = hashed
                db.session.commit()
            flash("Profile updated successfully!", "success")
        else:
            flash("No changes detected.", "info")
        return redirect(url_for('index'))

    # GET: prefill form
    u = User.query.get(user_id)
    user_tuple = (u.name, u.email) if u else ("", "")
    return render_template('profile.html', user=user_tuple)


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

    new_list = List(list_name=list_name, owner_id=user_id)
    db.session.add(new_list)
    db.session.commit()

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

    # fetch all owned and collaborated lists via SQLAlchemy
    lists = (
        db.session.query(
            List.list_id, List.list_name, User.name.label('owner_name')
        )
        .join(User, List.owner_id == User.user_id)
        .outerjoin(ListCollaborator, List.list_id == ListCollaborator.list_id)
        .filter((List.owner_id == user_id) | (ListCollaborator.user_id == user_id))
        .group_by(List.list_id, List.list_name, User.name)
        .order_by(List.list_id.asc())
        .all()
    )

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
    owner_list = List.query.get(list_id)
    if not owner_list or owner_list.owner_id != user_id:
        flash("You do not have permission to add collaborators.", "error")
        return redirect(url_for('index', list_id=list_id))

    # find the collaborator user_id by email
    collaborator = User.query.filter_by(email=collaborator_email).first()
    if not collaborator:
        flash("User not found.", "error")
        return redirect(url_for('index', list_id=list_id))

    collaborator_id = collaborator.user_id

    # prevent adding self
    if collaborator_id == user_id:
        flash("You cannot add yourself as collaborator.", "info")
        conn.close()
        return redirect(url_for('index', list_id=list_id))

    # add collaborator if not already exists
    try:
        db.session.add(ListCollaborator(list_id=list_id, user_id=collaborator_id))
        db.session.commit()
        flash(f"Added collaborator: {collaborator_email}", "success")
    except IntegrityError:
        db.session.rollback()
        flash("User is already a collaborator.", "info")
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
    lst = List.query.get(list_id)
    if not lst or lst.owner_id != user_id:
        flash("You do not have permission to remove collaborators.", "error")
        return redirect(url_for('index', list_id=list_id))

    # remove collaborator
    ListCollaborator.query.filter_by(list_id=list_id, user_id=collaborator_id).delete()
    db.session.commit()
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
    # app.run(debug=True, host='0.0.0.0')
    app.run(debug=True)
   


