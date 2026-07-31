"""
Starts the app. Inside Docker, this is what the web container runs.
"""
from tenant_app import create_app
from tenant_app.seed import ensure_database

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        ensure_database()
    app.run(host="0.0.0.0", port=5000)
