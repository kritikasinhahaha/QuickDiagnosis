"""
Vercel Serverless Function Entry Point for QuickDiagnosis
Exposes the Flask WSGI app for Vercel deployment.
"""

import sys
import os

# Add root folder to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

# Vercel looks for the WSGI application object 'app'
if __name__ == "__main__":
    app.run()
