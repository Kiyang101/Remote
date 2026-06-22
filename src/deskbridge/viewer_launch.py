# src/deskbridge/viewer_launch.py
"""Build and launch the VNC viewer for a target address.

Prefers the TigerVNC viewer (smooth, tunable) and exposes encoding settings as
simple quality presets. On macOS, falls back to the built-in Screen Sharing
client (`open vnc://`) when TigerVNC is not installed.
"""

import os
import subprocess

MACOS_TIGERVNC = "/Applications/TigerVNC.app/Contents/MacOS/vncviewer"

# Common to every preset: RemoteResize maps the remote 1:1 (fixes cursor offset);
# AlwaysCursor keeps the pointer visible.
_COMMON_FLAGS = ["-RemoteResize=1", "-AlwaysCursor=1"]

_PRESETS = {
    "fast": [
        "-PreferredEncoding=Tight",
        "-QualityLevel=4",
        "-CompressLevel=6",
        "-FullColor=0",
        "-LowColorLevel=1",
    ],
    "balanced": [
        "-PreferredEncoding=Tight",
        "-QualityLevel=7",
        "-CompressLevel=2",
        "-FullColor=1",
    ],
    "sharp": [
        "-PreferredEncoding=Tight",
        "-QualityLevel=9",
        "-CompressLevel=1",
        "-FullColor=1",
    ],
}


def quality_flags(quality: str) -> list[str]:
    """Map a quality preset name to TigerVNC viewer flags."""
    if quality not in _PRESETS:
        raise ValueError(f"Unknown quality preset: {quality!r}")
    return _COMMON_FLAGS + _PRESETS[quality]


def macos_tigervnc_path() -> str | None:
    """Return the macOS TigerVNC viewer binary path if installed, else None."""
    return MACOS_TIGERVNC if os.path.exists(MACOS_TIGERVNC) else None


def build_viewer_command(
    os_name: str,
    address: str,
    port: int = 5900,
    quality: str = "balanced",
    tigervnc_path: str | None = None,
) -> list[str]:
    """Return the argv list to launch the VNC viewer.

    macOS uses the TigerVNC viewer with quality flags when `tigervnc_path` is
    provided, otherwise falls back to the built-in client (`open vnc://`).
    Windows always uses the TigerVNC viewer (`host::port`) with quality flags.
    """
    if os_name == "macos":
        if tigervnc_path:
            return [tigervnc_path, f"{address}::{port}", *quality_flags(quality)]
        return ["open", f"vnc://{address}:{port}"]
    if os_name == "windows":
        exe = tigervnc_path or "vncviewer.exe"
        return [exe, f"{address}::{port}", *quality_flags(quality)]
    raise ValueError(f"No viewer mapping for OS: {os_name!r}")


def launch_viewer(
    os_name: str,
    address: str,
    port: int = 5900,
    quality: str = "balanced",
    tigervnc_path: str | None = None,
) -> subprocess.Popen:
    """Launch the viewer and return the process handle.

    On macOS, auto-detects the installed TigerVNC viewer when no path is given.
    """
    if os_name == "macos" and tigervnc_path is None:
        tigervnc_path = macos_tigervnc_path()
    cmd = build_viewer_command(os_name, address, port, quality, tigervnc_path)
    return subprocess.Popen(cmd)
