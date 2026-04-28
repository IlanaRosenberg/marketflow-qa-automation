import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    from seed_data.seed import seed_db
    with app.app_context():
        seed_db()
    print("MarketFlow running at http://localhost:5000")
    print("API docs at   http://localhost:5000/api/docs")
    app.run(host="0.0.0.0", port=5000, debug=True)
