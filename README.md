# cmsc128-IndivProject_Laserna

## This is Dooby, a to-do list made by Andrea Laserna.

I used Flask and SQLite as backend because I am comfortable with Python and it is easier for me to work with.

To run the app, make sure you are in the flask-server directory and run 

```
python app.py
```

### The following are API endpoints:

Home Page:
```
@app.route('/')
def index():
```

Add Tasks:
```
@app.route('/add_task', methods=['POST'])
def add_task_route():
```

Edit Tasks:
```
@app.route('/update_task/<int:id>', methods=['GET', 'POST'])
def edit_task_route(id):
```

Delete Tasks:
```
@app.route('/delete_task/<int:id>', methods=['GET']) 
def delete_task_route(id):
```

Toggle Tasks:
```
@app.route('/toggle_task/<int:id>', methods=['POST'])
def toggle_task_route(id):
```

Undo Task Delete:
```
@app.route('/undo_task_delete/<int:id>', methods=['GET', 'POST'])
def undo_task_delete_route(id):
```

### And here is the connection to the database:

```
DB_path = 'tasks.db'
conn = sqlite3.connect(DB_path)
```