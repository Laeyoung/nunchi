"""Vercel entry point: the public demo is cache-only. No API key is configured there, and LIVE is forced off
so a misconfigured environment can never spend credits."""
import os, sys

os.environ["LIVE"] = "0"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app  # noqa: E402,F401
