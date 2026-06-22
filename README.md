# DeskBridge

Two-way remote desktop between a Mac and a Windows PC. DeskBridge is the
connection manager; the actual screen sharing is done by each OS's VNC server
and the native VNC viewer.

## Install & run

    cd remote
    pip install -e .
    deskbridge          # or: python -m deskbridge.app

`pip install -e .` makes the `deskbridge` package importable and installs the
`deskbridge` command. Requires Python 3.10+; no third-party runtime dependencies.

## One-time setup per machine (host role)

Click **Share my screen** in the app for OS-specific steps:
- **macOS:** enable System Settings > General > Sharing > Screen Sharing (set a VNC password).
- **Windows:** install + start TigerVNC server (tigervnc.org), set a password, allow through the firewall.

## Connecting (controller role)

1. **Add** the other machine (name + host/IP).
2. Select it and click **Connect** — the native viewer opens; enter the VNC password.

macOS viewer is built in. On Windows, install the TigerVNC **viewer**; if
`vncviewer.exe` isn't on PATH the launch command can be pointed at its full path.

## Internet (v2)

Put both machines on the same Tailscale network; then add each machine by its
Tailscale name and the same Connect flow works across networks, encrypted.

## Tests

    cd remote
    python -m pytest -q
