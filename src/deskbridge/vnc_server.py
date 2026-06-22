"""Per-OS VNC server setup guidance and a local running check."""

from deskbridge.net import is_port_open

_MACOS_STEPS = """\
Enable the built-in VNC server (Screen Sharing) on this Mac:
1. Open System Settings > General > Sharing.
2. Turn on "Screen Sharing".
3. Click the (i) next to Screen Sharing > "Computer Settings…".
4. Tick "VNC viewers may control screen with password" and set a password.
5. Note this Mac's name/IP shown in the Sharing pane to give to the other machine.
"""

_WINDOWS_STEPS = """\
Install and start a VNC server (TigerVNC) on this Windows PC:
1. Download TigerVNC for Windows (tigervnc.org) and run the installer.
2. Start "TigerVNC Server" and set a connection password when prompted.
3. Allow it through Windows Firewall on the private network when asked.
4. Note this PC's IP (run `ipconfig`) to give to the other machine.
"""


def setup_instructions(os_name: str) -> str:
    """Return one-time setup steps for enabling the VNC server on this OS."""
    if os_name == "macos":
        return _MACOS_STEPS
    if os_name == "windows":
        return _WINDOWS_STEPS
    raise ValueError(f"No setup instructions for OS: {os_name!r}")


def is_server_running(port: int = 5900) -> bool:
    """Best-effort check that a VNC server is listening locally on this machine."""
    return is_port_open("127.0.0.1", port, timeout=0.5)
