CREATE TABLE IF NOT EXISTS promob_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    promob_name TEXT UNIQUE,
    target_type TEXT, -- 'material', 'item', or 'finish'
    target_id INTEGER,
    color_info TEXT,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS processed_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT UNIQUE,
    filename TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
