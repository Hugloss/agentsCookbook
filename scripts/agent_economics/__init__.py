"""Portable, stdlib-only agent economics probes.

These probes measure and rank evidence for coding agents. They never edit target
repository source code.
"""

from __future__ import annotations

from typing import Any

__all__ = ["context_focus_audit", "refactor_focus_audit"]


def __getattr__(name: str) -> Any:
    if name == "context_focus_audit":
        from .context_focus import context_focus_audit

        return context_focus_audit
    if name == "refactor_focus_audit":
        from .refactor_focus_workflow import refactor_focus_audit

        return refactor_focus_audit
    raise AttributeError(name)
