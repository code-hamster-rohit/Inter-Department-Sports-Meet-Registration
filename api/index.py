import os
import sys

# Add project root to sys.path so modules can be imported in serverless environments
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from main import app

# Vercel looks for the ASGI application variable 'app'
__all__ = ["app"]
