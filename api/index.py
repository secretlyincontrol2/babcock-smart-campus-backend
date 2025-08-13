"""
Vercel entrypoint for Flask app.
Expose the Flask WSGI app as `app` for @vercel/python.
Ensures the project root is on sys.path.
"""

import os
import sys

# Add project root (../) to sys.path so `app.*` imports work when running in serverless
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.flask_main import app  # Vercel detects `app` symbol


