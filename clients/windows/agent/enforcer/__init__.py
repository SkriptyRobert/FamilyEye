"""Rule enforcement package.

Refactored from monolithic enforcer.py (882 lines) for maintainability.
This __init__ re-exports RuleEnforcer for backward compatibility.
"""
from .core import RuleEnforcer

__all__ = ['RuleEnforcer']
