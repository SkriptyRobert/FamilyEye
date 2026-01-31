"""App monitoring package.

Refactored from monolithic monitor.py (717 lines).
Re-exports AppMonitor for compatibility.
"""
from .core import AppMonitor

__all__ = ['AppMonitor']
