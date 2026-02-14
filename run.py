from app import create_app
from app.database import init_db

app = create_app()

# Initialize Database (Create tables if needed)
init_db(app)

if __name__ == '__main__':
    # Use the new Scraper logic if needed, or let it run via separate worker
    # app/scraper.py has scraper_worker but it is not started by default in create_app
    # If we want to run it, we should start it here or in create_app
    
    # Check for debug mode from env or default to True for now (dev)
    app.run(debug=True, port=5000)
