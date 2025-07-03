"""
WSGI Entry Point for Production Deployment
This file is used by Gunicorn to serve the Flask application
"""
import os
import sys
from main import app

# Ensure the project directory is in Python path
if __name__ == "__main__":
    app.run()

# For Gunicorn: gunicorn wsgi:app
application = app
