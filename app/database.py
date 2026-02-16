import sqlite3
from flask import g

DATABASE = 'app.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db(app):
    with app.app_context():
        db = get_db()
        with app.open_resource('../schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        
        # Ensure Admin User
        try:
            db.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin', 'admin')")
            print("Admin user created (if not existed).")
        except sqlite3.IntegrityError:
            pass
            
        # Default Settings - seed if empty
        try:
             # Basic check if settings table exists via schema
             pass 
        except:
             pass
        db.commit()

def log_audit(user_id, action, details=''):
    db = get_db()
    db.execute('INSERT INTO audits (user_id, action, details) VALUES (?, ?, ?)',
               (user_id, action, details))
    db.commit()
