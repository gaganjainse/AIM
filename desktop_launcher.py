import threading
import time
import webbrowser

from waitress import serve

from app import app


def _open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:5000/login")


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    serve(app, host="127.0.0.1", port=5000)
