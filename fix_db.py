import sqlite3
import os

db_path = 'app.db'

if not os.path.exists(db_path):
    print("app.db not found!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Fix Orcamentos (Add Columns)
try:
    cursor.execute("SELECT prazo_entrega FROM orcamentos LIMIT 1")
    print("Col 'prazo_entrega' exists.")
except sqlite3.OperationalError:
    print("Adding 'prazo_entrega'...")
    cursor.execute("ALTER TABLE orcamentos ADD COLUMN prazo_entrega DATE")

try:
    cursor.execute("SELECT data_instalacao FROM orcamentos LIMIT 1")
    print("Col 'data_instalacao' exists.")
except sqlite3.OperationalError:
    print("Adding 'data_instalacao'...")
    cursor.execute("ALTER TABLE orcamentos ADD COLUMN data_instalacao DATE")

# 2. Fix Custos Fixos (Create Table)
try:
    cursor.execute("SELECT * FROM custos_fixos LIMIT 1")
    print("Table 'custos_fixos' exists.")
except sqlite3.OperationalError:
    print("Creating 'custos_fixos' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custos_fixos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            categoria TEXT
        )
    """)

conn.commit()
conn.close()
print("Database fix completed.")
