## Supabase/Postgres Configuration (Render)

- Preferred: set `DATABASE_URL` in Render to your Supabase Postgres connection string. Ensure it includes `sslmode=require` or the app will add it automatically.
- Alternatively set these env vars (supported locally via `.env` and on Render):
	- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (default 5432), `DB_NAME`.
- Local `.env` example (do not commit secrets):

```
SECRET_KEY=change-me
DB_USER=postgres.xxxxxxxx
DB_PASSWORD=your-strong-password
DB_HOST=aws-1-ap-southeast-1.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
```

The app prefers `DATABASE_URL` when present, otherwise it assembles a URL from the parts above and enforces `sslmode=require` for Supabase.

### Engine options for Supabase pooling
- Default: small connection pool (`pool_size=5`, `max_overflow=0`, `pool_pre_ping=True`).
- To disable client-side pooling (recommended for Transaction Pooler), set:

```
SQLALCHEMY_DISABLE_POOL=1
```

- Optional tuning:

```
SQLALCHEMY_POOL_SIZE=5
SQLALCHEMY_MAX_OVERFLOW=0
SQLALCHEMY_POOL_RECYCLE=300
```

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