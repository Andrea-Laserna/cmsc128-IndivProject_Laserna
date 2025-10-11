from flask import Flask, flash, render_template, request, redirect, url_for
from datetime import datetime
from dotenv import load_dotenv
import os
import sqlite3

# load variables from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

DB_path = 'tasks.db'

# creating the table
def init_db():
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor() # allows python to speak to sqlite
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            task TEXT NOT NULL,
            isChecked BIT DEFAULT 0,
            priority TEXT NOT NULL,
            deadline DATETIME NOT NULL,
            created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
            is_deleted BIT DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# helper functions

# retrieve all tasks with default sorting option
def get_tasks(sort="created-at", order="desc"):
    # security purposes lol
    allowed_sorts = {"priority", "created_at", "deadline"}
    allowed_order = {"asc", "desc"}

    if sort not in allowed_sorts:
        sort = "created-at"
    if order not in allowed_order:
        order = "desc"

    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()

    if sort == "priority":
        cursor.execute('''
            SELECT * FROM tasks 
                WHERE is_deleted = 0
                ORDER BY CASE priority 
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END ASC
            ''')
    else:
        cursor.execute(f'SELECT * FROM tasks WHERE is_deleted = 0 ORDER BY {sort} {order.upper()}')

    tasks = cursor.fetchall()
    cursor.close()
    return tasks

# add a task
def add_task(task, priority, deadline):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (task, priority, deadline) VALUES(?, ?, ?)', (task, priority, deadline))
    conn.commit()
    cursor.close()

# edit task
def edit_task(id, task, priority, deadline):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET task = ?, priority = ?, deadline = ? WHERE id = ?', (task, priority, deadline, id))
    conn.commit()
    cursor.close()

# delete task
def delete_task(id):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET is_deleted = 1 WHERE id = ?', (id,))
    conn.commit()
    cursor.close()

# toggle task checkbox
def toggle_task(id, isChecked):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET isChecked = ? WHERE id = ?', (isChecked, id))
    conn.commit()
    cursor.close()

# undo delete task
def undo_task_delete(id):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET is_deleted = 0 WHERE id = ?', (id,))
    conn.commit()
    cursor.close()

# flask connections

# home page
@app.route('/')
def index():
    sort = request.args.get("sort", "created_at")
    order = request.args.get("order", "desc")
    tasks = get_tasks(sort, order) # includes sorting and order option
    return render_template("index.html", tasks=tasks)

# adding tasks
@app.route('/add_task', methods=['POST'])
def add_task_route():
    task = request.form['task']
    priority = request.form['priority']
    deadline = request.form['deadline']
    add_task(task, priority, deadline)
    return redirect(url_for('index')) 

# edit tasks
@app.route('/update_task/<int:id>', methods=['GET', 'POST'])
def edit_task_route(id):
    task = request.form['task']
    priority = request.form['priority']
    deadline = request.form['deadline']
    edit_task(id, task, priority, deadline)
    return redirect(url_for('index')) 

# delete tasks
@app.route('/delete_task/<int:id>', methods=['GET']) 
def delete_task_route(id):
    delete_task(id)
    # toast
    flash(f"Task deleted! <a href='{url_for('undo_task_delete_route', id=id)}' class='btn undo-btn'>Undo</a>", "undo")
    return redirect(url_for('index'))

# toggle tasks
@app.route('/toggle_task/<int:id>', methods=['POST'])
def toggle_task_route(id):
    isChecked = int(request.form['isChecked'])
    toggle_task(id, isChecked)
    return '', 204 # no content

# undo task delete
@app.route('/undo_task_delete/<int:id>', methods=['GET', 'POST'])
def undo_task_delete_route(id):
    undo_task_delete(id)
    return redirect(url_for('index')) 

# run
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
   


