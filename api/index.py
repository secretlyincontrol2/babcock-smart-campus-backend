"""
Vercel entrypoint for Flask app.
Expose the Flask WSGI app as `app` for @vercel/python.
"""

from app.flask_main import app  # Vercel detects `app` symbol


