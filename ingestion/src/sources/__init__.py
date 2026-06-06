"""Per-source extractors. Each module exposes a single fetch_* function that
returns a tidy (long) pandas DataFrame; it does NOT know about the lake or
watermarks -- the orchestrator in extract.py wires those together."""
