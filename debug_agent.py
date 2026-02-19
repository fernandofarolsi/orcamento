from flask import Flask
from app.services import camila_agent
import traceback

app = Flask(__name__)

# Need app context for database access
with app.app_context():
    # Mocking database connection if needed, but get_db uses g, so we might need to mock request
    # However, get_db in app.database creates a new connection if not present, so app_context should be enough if configured
    
    # We need to configure the app to know where the DB is
    app.config['DATABASE'] = 'app/app.db'
    
    try:
        # Assuming chat_id=1 exists or use the one created
        print("Testing process_message with tool use (amadeirado)...")
        # Trigger a tool use case
        camila_agent.process_message(1, "Vocês tem algum MDF tom amadeirado?", is_simulation=True)
        # We need to capture the response, but process_message doesn't return it
        # It updates DB and sends it via waha. 
        # Ideally, we mock waha or check DB
        
        db = camila_agent.get_db()
        last_msg = db.execute("SELECT content FROM whatsapp_messages WHERE chat_id = 1 AND sender = 'camila' ORDER BY timestamp DESC LIMIT 1").fetchone()
        if last_msg:
            print(f"Response: {last_msg['content']}")
        else:
            print("No response found in DB")
            
        print("Success!")
    except Exception:
        traceback.print_exc()
