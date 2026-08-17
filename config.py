"""Backward-compatible top-level config import for AURA.

New backend code should import from ``backend.config.config``. This file exists
so scripts and tests can also use ``import config`` as requested by the project
brief.
"""

from backend.config.config import Settings, settings

__all__ = ["Settings", "settings"]
