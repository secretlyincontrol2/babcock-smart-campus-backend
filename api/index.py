"""
Vercel entrypoint for Flask app using vercel-wsgi adapter.
"""

from vercel_wsgi import make_wsgi_handler
from app.flask_main import app

# Vercel expects `handler` as the entrypoint
handler = make_wsgi_handler(app)


