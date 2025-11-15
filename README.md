# cmsc128-IndivProject_Laserna

## This is Dooby, a to-do list made by Andrea Laserna.

I used Flask and SQLite as backend because I am comfortable with Python and it is easier for me to work with. I've worked with SQLite before in a discord bot I built a year ago...

To run the app, make sure you are in the flask-server directory and run the command below in the terminal

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

Sign Up Page:
```
@app.route('/signup', methods=['POST', 'GET'])
def signup():
```

Login Page:
```
@app.route('/login', methods=['POST', 'GET'])
def login():
```

Forgot Password:
```
@app.route('/forgot_password', methods = ['GET', 'POST'])
def forgot_password():
```

Reset Link:
```
@app.route('/show_reset_link')
def show_reset_link():
```

Reset Password:
```
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
```

Profile Page:
```
@app.route('/profile', methods=['GET', 'POST'])
def profile():
```

Logout:
```
@app.route('/logout')
def logout():
```

Create List:
```
@app.route('/create_list', methods=['POST'])
def create_list():
```

Collaboration:
```
@app.route('/collaboration')
def collaboration():
```

Add Collaborator:
```
@app.route('/add_collaborator', methods=['POST'])
def add_collaborator():
```

Remove Collaborator:
```
@app.route('/remove_collaborator', methods=['POST'])
def remove_collaborator():
```

### And here is the connection to the database:

```
DB_path = 'tasks.db'
conn = sqlite3.connect(DB_path)
```