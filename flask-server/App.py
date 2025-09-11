from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

DB_path = "C:\\Users\\ASUS\\Desktop\\BSCS 4-1st Sem\\CMSC 128\\cmsc128-IndivProject_Laserna\\tasks.db"

# Setup DB
def init_db():
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            task TEXT NOT NULL,
            priority TEXT NOT NULL,
            deadline DATETIME NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks')
    tasks = cursor.fetchall()
    conn.close()
    return tasks


def add_task(task, priority, deadline):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (task, priority, deadline) VALUES (?, ?, ?)', (task, priority, deadline))
    conn.commit()
    conn.close()

def update_task(id, task, priority, deadline):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET task = ?, priority = ?, deadline = ? WHERE id = ?', (task, priority, deadline, id))
    conn.commit()
    conn.close()

def delete_task(id):
    conn = sqlite3.connect(DB_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (id,))
    conn.commit()
    conn.close()

# Home page
@app.route('/')
def index():
    tasks = get_tasks()
    return render_template("index.html", tasks=tasks) 

# Add task via POST request
@app.route('/add_task', methods=['POST'])
def add_task_route():
    task = request.form['task']
    priority = request.form['priority']    
    deadline = request.form['deadline']
    add_task(task, priority, deadline)
    return redirect(url_for('index'))

# Update task via GET and POST request
@app.route('/update_task/<int:id>', methods = ['GET', 'POST'])
def update_task_route(id):
    task = request.form['task']
    priority = request.form['priority']
    deadline = request.form['deadline']
    update_task(id, task, priority, deadline)
    return redirect(url_for('index'))

# Delete tasks via GET request
@app.route('/delete_task/<int:id>', methods = ['GET'])
def delete_task_route(id):
    delete_task(id)
    return redirect(url_for('index'))

# Run
if __name__ == "__main__":
    init_db()
    app.run(debug=True)