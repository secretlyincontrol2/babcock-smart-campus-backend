"""
Compatibility shim: expose Flask app as `app` so any references to `app.main:app` work.
"""

from .flask_main import app  # noqa: F401

