"""Snapshot collection layer.

This is the ONLY part of the project that touches the network. It runs once
per collection campaign (see scripts/01_snapshot.py) and produces the
immutable raw snapshot under data/raw/. Every downstream pipeline stage is a
pure function over that snapshot.
"""
