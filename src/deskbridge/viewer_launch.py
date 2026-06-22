# src/deskbridge/viewer_launch.py
"""Build and launch the OS-native VNC viewer for a target address."""

import subprocess


def build_viewer_command(
    os_name: str,
    address: str,
    port: int = 5900,
    tigervnc_path: str | None = None,
) -> list[str]:
    """Return the argv list to launch the native VNC viewer.

    macOS uses the built-in Screen Sharing client via `open vnc://`.
    Windows uses the TigerVNC viewer (`host::port`).
    """
    if os_name == "macos":
        return ["open", f"vnc://{address}:{port}"]
    if os_name == "windows":
        exe = tigervnc_path or "vncviewer.exe"
        return [exe, f"{address}::{port}"]
    raise ValueError(f"No native viewer mapping for OS: {os_name!r}")


def launch_viewer(
    os_name: str,
    address: str,
    port: int = 5900,
    tigervnc_path: str | None = None,
) -> subprocess.Popen:
    """Launch the native viewer and return the process handle."""
    cmd = build_viewer_command(os_name, address, port, tigervnc_path)
    return subprocess.Popen(cmd)
