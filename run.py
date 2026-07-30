"""
Double-click (or run) this file to start the pilot.

It will:
  1. Create the database and fill it with sample data, if that hasn't
     happened yet.
  2. Start the web app on your own computer only (not visible to anyone
     else on the internet).
  3. Automatically open your web browser to the application form.

To stop the app, go back to the terminal window and press Ctrl+C.
"""
import threading
import webbrowser

from app import app
from seed import ensure_database

URL = "http://127.0.0.1:5000/apply"


def open_browser():
    webbrowser.open(URL)


if __name__ == "__main__":
    ensure_database()
    threading.Timer(1.25, open_browser).start()
    print("\nStarting the tenant application pilot...")
    print(f"If your browser doesn't open automatically, go to: {URL}")
    print("Decision-maker login is at: http://127.0.0.1:5000/admin/login")
    print("Press Ctrl+C in this window to stop the app.\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
