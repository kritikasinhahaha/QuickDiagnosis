"""
Vercel Serverless Function Entry Point for QuickDiagnosis
Exposes the FastAPI ASGI application for Vercel deployment.
"""

import sys
import os

# Add root folder to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.main import app

# Vercel automatically exposes the FastAPI ASGI application 'app'

