"""Host-neutral semantic classification for repository tool-routing evidence."""

from __future__ import annotations

import re
from typing import Any

SUBJECT_REPOSITORY_INTELLIGENCE = "subject-repository-intelligence"
NATIVE_SEARCH = "native-search"
NATIVE_READ = "native-read"
SHELL = "shell"
TOOL_ROUTER = "tool-router"
OTHER = "other"

DISCOVERY_CLASSES = frozenset({NATIVE_SEARCH, NATIVE_READ, SHELL})

_SEARCH_OPERATIONS = frozenset({
    "grep",
    "glob",
    "search",
    "search_code",
    "find",
    "find_files",
    "list_files",
})
_READ_OPERATIONS = frozenset({
    "read",
    "read_file",
    "fetch_file",
    "get_file",
    "open_file",
})
_SHELL_OPERATIONS = frozenset({
    "bash",
    "shell",
    "terminal",
    "run_command",
})
_ROUTER_OPERATIONS = frozenset({
    "execute",
    "exec",
    "functions_exec",
})

_SEPARATOR = re.compile(r"(?:::|__|[./])+")


def tool_tokens(name: object) -> tuple[str, ...]:
    if not isinstance(name, str):
        return ()
    normalized = name.strip().lower().replace("-", "_")
    if not normalized:
        return ()
    return tuple(token for token in _SEPARATOR.split(normalized) if token)


def _subject_tokens(subject: object) -> tuple[str, ...]:
    if not isinstance(subject, str):
        return ()
    value = subject.strip().lower().replace("-", "_")
    return (value,) if value and value != "none" else ()


def is_subject_tool(name: object, subject: object) -> bool:
    tokens = tool_tokens(name)
    subject_tokens = _subject_tokens(subject)
    if not tokens or not subject_tokens:
        return False
    selected = subject_tokens[0]
    if selected in tokens:
        return True
    rendered = "_".join(tokens)
    return rendered.startswith(selected + "_")


def _operation_candidates(tokens: tuple[str, ...]) -> tuple[str, ...]:
    if not tokens:
        return ()
    candidates = [tokens[-1]]
    if len(tokens) >= 2:
        candidates.append("_".join(tokens[-2:]))
    return tuple(dict.fromkeys(candidates))


def matches_subject_operation(
    name: object,
    *,
    subject: object,
    operation: str,
) -> bool:
    if not is_subject_tool(name, subject):
        return False
    tokens = tool_tokens(name)
    normalized = operation.strip().lower().replace("-", "_")
    selected = _subject_tokens(subject)[0]
    rendered = "_".join(tokens)
    return (
        normalized in _operation_candidates(tokens)
        or rendered == f"{selected}_{normalized}"
        or rendered.endswith(f"_{selected}_{normalized}")
    )


def classify_tool(name: object, *, subject: object = None) -> str:
    """Map host-specific tool names into one routing-scoring vocabulary."""
    if is_subject_tool(name, subject):
        return SUBJECT_REPOSITORY_INTELLIGENCE

    tokens = tool_tokens(name)
    candidates = _operation_candidates(tokens)
    if any(candidate in _SEARCH_OPERATIONS for candidate in candidates):
        return NATIVE_SEARCH
    if any(candidate in _READ_OPERATIONS for candidate in candidates):
        return NATIVE_READ
    if any(candidate in _SHELL_OPERATIONS for candidate in candidates):
        return SHELL
    if any(candidate in _ROUTER_OPERATIONS for candidate in candidates):
        return TOOL_ROUTER
    return OTHER


def classify_call(
    name: object,
    inputs: object = None,
    *,
    subject: object = None,
) -> str:
    """Classify a concrete call, including generic API discovery surfaces."""
    base = classify_tool(name, subject=subject)
    if base != OTHER:
        return base
    if not isinstance(inputs, dict):
        return base

    tokens = tool_tokens(name)
    operation = tokens[-1] if tokens else ""
    url = inputs.get("url")
    if operation == "fetch" and isinstance(url, str):
        lowered = url.lower()
        if "/git/trees/" in lowered or "/search/code" in lowered:
            return NATIVE_SEARCH
        if "/contents/" in lowered or "/git/blobs/" in lowered:
            return NATIVE_READ
    return base


def first_discovery_index(calls: list[dict[str, Any]]) -> int:
    return next(
        (
            index
            for index, call in enumerate(calls)
            if call.get("tool_class") in DISCOVERY_CLASSES
        ),
        len(calls),
    )


def catalog_admission(
    tool_names: list[str] | tuple[str, ...],
    *,
    subject: str,
    required_tool: str,
) -> dict[str, object]:
    """Classify whether one host catalog can measure subject-first routing."""
    operation = required_tool.removeprefix(subject + "_")
    required_visible = any(
        matches_subject_operation(
            name,
            subject=subject,
            operation=operation,
        )
        for name in tool_names
    )
    native_classes = sorted({
        classify_tool(name, subject=subject)
        for name in tool_names
        if classify_tool(name, subject=subject) in DISCOVERY_CLASSES
    })
    reasons: list[str] = []
    if not required_visible:
        reasons.append("required-subject-tool-missing")
    if not native_classes:
        reasons.append("native-discovery-tools-missing")
    return {
        "schema": "agents-cookbook-tool-routing-catalog.v1",
        "status": "READY" if not reasons else "ENVIRONMENT_BLOCKED",
        "subject": subject,
        "required_tool": required_tool,
        "required_tool_visible": required_visible,
        "native_discovery_classes": native_classes,
        "reason_codes": reasons,
    }
