"""Vercel serverless entry point for AIM demo page.

This serves a demo landing page explaining that AIM requires a MySQL database
to function. The full application with MySQL is available for local deployment.
"""
from flask import Flask, render_template
import os

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))


@app.route("/")
@app.route("/<path:path>")
def demo(path=None):
    return render_template("demo.html")


@app.route("/health")
def health():
    return {"status": "ok", "mode": "demo"}
