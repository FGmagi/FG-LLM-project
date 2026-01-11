#!/usr/bin/env python3
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT)

from .app import start_server

if __name__ == "__main__":
    start_server()
