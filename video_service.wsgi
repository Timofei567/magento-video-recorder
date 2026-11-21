"""WSGI entry point used by Apache mod_wsgi."""
import sys

sys.path.insert(0, "/app")

from web_service import app as application
