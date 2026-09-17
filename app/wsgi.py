"""WSGI entry point.

Used as the gunicorn target (``app.wsgi:app``) by both start.sh and a
pipx/pip install. Kept separate from the root-level ``run.py`` because
``run.py`` lives outside the ``app`` package and is not shipped when the
project is installed as a package (pipx/pip) rather than run from a git
checkout.
"""
from app import create_app

app = create_app()
