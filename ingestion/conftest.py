"""Pytest bootstrap: put the ingestion/ directory on sys.path so tests can
`import src...` the same way extract.py does."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
