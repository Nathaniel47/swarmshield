"""Where the app keeps files it writes. Both locations can be moved with environment variables so
the container can point them at a writable folder (its root filesystem is read-only)."""

import os
from pathlib import Path

STATE_DIR = Path(os.environ.get("SWARMSHIELD_STATE_DIR", "results"))  # SQLite files
CACHE_DIR = Path(os.environ.get("SWARMSHIELD_CACHE_DIR", "llm_cache"))  # model replies, usage
