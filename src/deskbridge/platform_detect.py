"""Detect and normalize the host operating system."""

import platform


def normalize_os(system_name: str) -> str:
    """Map platform.system() output to 'macos' | 'windows' | 'other'."""
    mapping = {"Darwin": "macos", "Windows": "windows"}
    return mapping.get(system_name, "other")


def current_os() -> str:
    """Return the normalized OS name for the machine we're running on."""
    return normalize_os(platform.system())
