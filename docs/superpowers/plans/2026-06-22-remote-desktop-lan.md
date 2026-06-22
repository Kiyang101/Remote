# Remote Desktop (Mac ⇄ Windows) — v1 LAN Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build DeskBridge v1 — a dependency-light Python app that lets a Mac and a Windows PC control each other's desktop over the LAN by managing connections and launching the OS-native VNC viewer.

**Architecture:** A small Tkinter app is the "brain" on top of reused components. It detects the OS, stores a list of machines in JSON, checks reachability, and launches the native VNC viewer (`open vnc://…` on macOS, TigerVNC viewer on Windows) pointed at the chosen machine. Screen capture/encoding/input is handled by the OS VNC server (mac Screen Sharing / Windows TigerVNC), which is set up once via a wizard. Internet support (Tailscale) is deferred to v2.

**Tech Stack:** Python 3 (standard library only), Tkinter for GUI, `pytest` for tests. No third-party runtime dependencies.

---

## File Structure

```
remote/
  src/deskbridge/
    __init__.py
    platform_detect.py   # which OS am I on
    connections.py       # Connection model + JSON load/save
    net.py               # resolve address + TCP reachability check
    viewer_launch.py     # build/launch native VNC viewer command per OS
    vnc_server.py        # server status + per-OS setup instructions
    gui.py               # Tkinter connection-manager window
    app.py               # entry point: wires modules into the GUI
  tests/
    test_platform_detect.py
    test_connections.py
    test_net.py
    test_viewer_launch.py
    test_vnc_server.py
  pyproject.toml
  README.md
```

Each module has one responsibility and a small, testable interface. `gui.py` and
`app.py` are the only side-effect-heavy / manual-test files; everything else is
unit-tested pure logic.

---

### Task 1: Project scaffolding

**Files:**
- Create: `remote/pyproject.toml`
- Create: `remote/src/deskbridge/__init__.py`
- Create: `remote/tests/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "deskbridge"
version = "0.1.0"
description = "Two-way Mac/Windows remote desktop via VNC + native viewers"
requires-python = ">=3.10"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create empty package files**

Create `remote/src/deskbridge/__init__.py` with:

```python
"""DeskBridge — two-way Mac/Windows remote desktop over VNC."""

__version__ = "0.1.0"
```

Create `remote/tests/__init__.py` as an empty file.

- [ ] **Step 3: Verify pytest runs (collects nothing)**

Run: `cd remote && python -m pytest -q`
Expected: `no tests ran` (exit code 5) — confirms pytest + pythonpath config load without error.

- [ ] **Step 4: Commit**

```bash
cd remote
git add pyproject.toml src/deskbridge/__init__.py tests/__init__.py
git commit -m "chore: scaffold deskbridge package and pytest config"
```

---

### Task 2: Platform detection

**Files:**
- Create: `remote/src/deskbridge/platform_detect.py`
- Test: `remote/tests/test_platform_detect.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_platform_detect.py
from deskbridge.platform_detect import normalize_os


def test_normalize_macos():
    assert normalize_os("Darwin") == "macos"


def test_normalize_windows():
    assert normalize_os("Windows") == "windows"


def test_normalize_other():
    assert normalize_os("Linux") == "other"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd remote && python -m pytest tests/test_platform_detect.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deskbridge.platform_detect'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/deskbridge/platform_detect.py
"""Detect and normalize the host operating system."""

import platform


def normalize_os(system_name: str) -> str:
    """Map platform.system() output to 'macos' | 'windows' | 'other'."""
    mapping = {"Darwin": "macos", "Windows": "windows"}
    return mapping.get(system_name, "other")


def current_os() -> str:
    """Return the normalized OS name for the machine we're running on."""
    return normalize_os(platform.system())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd remote && python -m pytest tests/test_platform_detect.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd remote
git add src/deskbridge/platform_detect.py tests/test_platform_detect.py
git commit -m "feat: add OS detection"
```

---

### Task 3: Connection model + JSON persistence

**Files:**
- Create: `remote/src/deskbridge/connections.py`
- Test: `remote/tests/test_connections.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_connections.py
from deskbridge.connections import Connection, load_connections, save_connections


def test_roundtrip(tmp_path):
    path = tmp_path / "connections.json"
    conns = [
        Connection(name="My Windows", host="192.168.1.42", port=5900, notes="desk PC"),
        Connection(name="My Mac", host="mac.local", port=5900),
    ]
    save_connections(path, conns)
    loaded = load_connections(path)
    assert loaded == conns


def test_load_missing_file_returns_empty(tmp_path):
    assert load_connections(tmp_path / "nope.json") == []


def test_defaults():
    c = Connection(name="x", host="h")
    assert c.port == 5900
    assert c.tailscale_name is None
    assert c.notes == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd remote && python -m pytest tests/test_connections.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deskbridge.connections'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/deskbridge/connections.py
"""Connection model and JSON persistence for saved machines."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Connection:
    name: str
    host: str
    port: int = 5900
    tailscale_name: str | None = None
    notes: str = ""


def default_config_path() -> Path:
    """Location of the saved-connections file under the user's home."""
    return Path.home() / ".deskbridge" / "connections.json"


def load_connections(path: Path) -> list[Connection]:
    """Load connections from JSON; return [] if the file does not exist."""
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [Connection(**item) for item in data]


def save_connections(path: Path, connections: list[Connection]) -> None:
    """Write connections to JSON, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(c) for c in connections], indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd remote && python -m pytest tests/test_connections.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd remote
git add src/deskbridge/connections.py tests/test_connections.py
git commit -m "feat: add connection model and JSON persistence"
```

---

### Task 4: Address resolution + reachability check

**Files:**
- Create: `remote/src/deskbridge/net.py`
- Test: `remote/tests/test_net.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_net.py
from unittest import mock

from deskbridge.connections import Connection
from deskbridge.net import resolve_address, is_port_open


def test_resolve_prefers_lan_host_by_default():
    c = Connection(name="x", host="192.168.1.5", tailscale_name="x-ts")
    assert resolve_address(c, use_tailscale=False) == "192.168.1.5"


def test_resolve_uses_tailscale_when_requested():
    c = Connection(name="x", host="192.168.1.5", tailscale_name="x-ts")
    assert resolve_address(c, use_tailscale=True) == "x-ts"


def test_resolve_falls_back_to_host_when_no_tailscale_name():
    c = Connection(name="x", host="192.168.1.5", tailscale_name=None)
    assert resolve_address(c, use_tailscale=True) == "192.168.1.5"


def test_is_port_open_true_when_connect_succeeds():
    fake_sock = mock.MagicMock()
    with mock.patch("socket.create_connection", return_value=fake_sock) as cc:
        assert is_port_open("host", 5900, timeout=0.1) is True
        cc.assert_called_once()


def test_is_port_open_false_on_oserror():
    with mock.patch("socket.create_connection", side_effect=OSError):
        assert is_port_open("host", 5900, timeout=0.1) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd remote && python -m pytest tests/test_net.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deskbridge.net'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/deskbridge/net.py
"""Resolve a connection to a reachable address and test VNC reachability."""

import socket

from deskbridge.connections import Connection


def resolve_address(conn: Connection, use_tailscale: bool) -> str:
    """Pick the address to connect to: Tailscale name if requested+available,
    otherwise the LAN host."""
    if use_tailscale and conn.tailscale_name:
        return conn.tailscale_name
    return conn.host


def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd remote && python -m pytest tests/test_net.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
cd remote
git add src/deskbridge/net.py tests/test_net.py
git commit -m "feat: add address resolution and TCP reachability check"
```

---

### Task 5: Native viewer launch command

**Files:**
- Create: `remote/src/deskbridge/viewer_launch.py`
- Test: `remote/tests/test_viewer_launch.py`

Notes on viewer invocation:
- **macOS:** `open vnc://<address>:<port>` opens the built-in Screen Sharing client.
- **Windows:** TigerVNC viewer uses `vncviewer <address>::<port>` (double colon forces a raw TCP port rather than a display number).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_viewer_launch.py
import pytest

from deskbridge.viewer_launch import build_viewer_command


def test_macos_command():
    cmd = build_viewer_command("macos", "192.168.1.5", 5900)
    assert cmd == ["open", "vnc://192.168.1.5:5900"]


def test_windows_command_default_path():
    cmd = build_viewer_command("windows", "192.168.1.5", 5901)
    assert cmd == ["vncviewer.exe", "192.168.1.5::5901"]


def test_windows_command_custom_path():
    cmd = build_viewer_command(
        "windows", "host", 5900, tigervnc_path=r"C:\Tools\vncviewer.exe"
    )
    assert cmd == [r"C:\Tools\vncviewer.exe", "host::5900"]


def test_unsupported_os_raises():
    with pytest.raises(ValueError):
        build_viewer_command("other", "host", 5900)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd remote && python -m pytest tests/test_viewer_launch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deskbridge.viewer_launch'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd remote && python -m pytest tests/test_viewer_launch.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd remote
git add src/deskbridge/viewer_launch.py tests/test_viewer_launch.py
git commit -m "feat: build native VNC viewer launch commands"
```

---

### Task 6: VNC server status + setup instructions

**Files:**
- Create: `remote/src/deskbridge/vnc_server.py`
- Test: `remote/tests/test_vnc_server.py`

This module returns human-readable setup steps and a best-effort "is the server
likely running" check. Enabling the server is a one-time manual action guided by
the wizard text (we do not silently flip OS security settings).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vnc_server.py
from unittest import mock

import pytest

from deskbridge.vnc_server import setup_instructions, is_server_running


def test_macos_instructions_mention_screen_sharing():
    text = setup_instructions("macos")
    assert "Screen Sharing" in text


def test_windows_instructions_mention_tigervnc():
    text = setup_instructions("windows")
    assert "TigerVNC" in text


def test_unsupported_os_raises():
    with pytest.raises(ValueError):
        setup_instructions("other")


def test_is_server_running_checks_local_port():
    with mock.patch("deskbridge.vnc_server.is_port_open", return_value=True) as p:
        assert is_server_running(5900) is True
        p.assert_called_once_with("127.0.0.1", 5900, timeout=0.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd remote && python -m pytest tests/test_vnc_server.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deskbridge.vnc_server'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/deskbridge/vnc_server.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd remote && python -m pytest tests/test_vnc_server.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd remote
git add src/deskbridge/vnc_server.py tests/test_vnc_server.py
git commit -m "feat: add VNC server setup instructions and local running check"
```

---

### Task 7: Tkinter connection-manager GUI

**Files:**
- Create: `remote/src/deskbridge/gui.py`

This is GUI code verified by manual run (Step 3), not unit tests. It depends only
on the interfaces already defined: `current_os`, `load_connections`/`save_connections`/
`Connection`, `resolve_address`/`is_port_open`, `launch_viewer`, `setup_instructions`/
`is_server_running`.

- [ ] **Step 1: Write the GUI module**

```python
# src/deskbridge/gui.py
"""Tkinter connection-manager window for DeskBridge."""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

from deskbridge.connections import (
    Connection,
    load_connections,
    save_connections,
)
from deskbridge.net import is_port_open, resolve_address
from deskbridge.platform_detect import current_os
from deskbridge.viewer_launch import launch_viewer
from deskbridge.vnc_server import is_server_running, setup_instructions


class DeskBridgeApp:
    def __init__(self, root: tk.Tk, config_path: Path):
        self.root = root
        self.config_path = config_path
        self.os_name = current_os()
        self.connections = load_connections(config_path)

        root.title("DeskBridge")
        root.geometry("420x360")

        tk.Label(root, text=f"This machine: {self.os_name}").pack(anchor="w", padx=8, pady=4)

        self.listbox = tk.Listbox(root)
        self.listbox.pack(fill="both", expand=True, padx=8, pady=4)
        self._refresh_list()

        btns = tk.Frame(root)
        btns.pack(fill="x", padx=8, pady=4)
        tk.Button(btns, text="Connect", command=self.connect).pack(side="left")
        tk.Button(btns, text="Add", command=self.add_machine).pack(side="left")
        tk.Button(btns, text="Remove", command=self.remove_machine).pack(side="left")
        tk.Button(btns, text="Share my screen", command=self.share_screen).pack(side="right")

        self.status = tk.Label(root, text="", anchor="w", fg="gray")
        self.status.pack(fill="x", padx=8, pady=4)

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for c in self.connections:
            self.listbox.insert(tk.END, f"{c.name} — {c.host}:{c.port}")

    def _selected(self) -> Connection | None:
        sel = self.listbox.curselection()
        return self.connections[sel[0]] if sel else None

    def connect(self):
        conn = self._selected()
        if not conn:
            self.status.config(text="Select a machine first.")
            return
        address = resolve_address(conn, use_tailscale=False)
        self.status.config(text=f"Checking {address}:{conn.port}…")
        self.root.update_idletasks()
        if not is_port_open(address, conn.port, timeout=2.0):
            messagebox.showwarning(
                "Unreachable",
                f"Could not reach {address}:{conn.port}.\n\n"
                "Check the machine is on and its VNC server is running.",
            )
            self.status.config(text="Unreachable.")
            return
        launch_viewer(self.os_name, address, conn.port)
        self.status.config(text=f"Launched viewer for {conn.name}.")

    def add_machine(self):
        name = simpledialog.askstring("Add machine", "Name:", parent=self.root)
        if not name:
            return
        host = simpledialog.askstring("Add machine", "Host or IP:", parent=self.root)
        if not host:
            return
        self.connections.append(Connection(name=name, host=host))
        save_connections(self.config_path, self.connections)
        self._refresh_list()

    def remove_machine(self):
        conn = self._selected()
        if not conn:
            return
        self.connections.remove(conn)
        save_connections(self.config_path, self.connections)
        self._refresh_list()

    def share_screen(self):
        running = is_server_running()
        steps = setup_instructions(self.os_name)
        prefix = "VNC server appears to be running.\n\n" if running else ""
        messagebox.showinfo("Share my screen", prefix + steps)
```

- [ ] **Step 2: Sanity-check it imports**

Run: `cd remote && python -c "import deskbridge.gui"`
Expected: no output, exit code 0 (module imports cleanly).

- [ ] **Step 3: Manual smoke test (after Task 8 wires the entry point)**

Deferred to Task 8's manual checklist (the GUI needs `app.py` to launch a window).

- [ ] **Step 4: Commit**

```bash
cd remote
git add src/deskbridge/gui.py
git commit -m "feat: add Tkinter connection-manager GUI"
```

---

### Task 8: Entry point, README, and manual integration test

**Files:**
- Create: `remote/src/deskbridge/app.py`
- Create: `remote/README.md`

- [ ] **Step 1: Write the entry point**

```python
# src/deskbridge/app.py
"""DeskBridge entry point: launch the connection-manager window."""

import tkinter as tk

from deskbridge.connections import default_config_path
from deskbridge.gui import DeskBridgeApp


def main() -> None:
    root = tk.Tk()
    DeskBridgeApp(root, default_config_path())
    root.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write the README**

```markdown
# DeskBridge

Two-way remote desktop between a Mac and a Windows PC. DeskBridge is the
connection manager; the actual screen sharing is done by each OS's VNC server
and the native VNC viewer.

## Run

    cd remote
    python -m deskbridge.app

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
```

- [ ] **Step 3: Run the full unit test suite**

Run: `cd remote && python -m pytest -q`
Expected: PASS — all tests from Tasks 2–6 green (no failures).

- [ ] **Step 4: Manual GUI smoke test**

Run: `cd remote && python -m deskbridge.app`
Expected: a DeskBridge window opens showing "This machine: macos" (or windows).
Verify: **Add** a machine (it appears in the list and persists after reopening),
**Share my screen** shows the OS setup steps, **Connect** to an unreachable host
shows the "Unreachable" warning. Close the window.

- [ ] **Step 5: Manual end-to-end test (two real machines on the LAN)**

Checklist (record pass/fail in the commit message or a note):
1. On the Mac: enable Screen Sharing with a VNC password.
2. On Windows: add the Mac (its `.local` name or IP) → Connect → enter password →
   confirm you can see and control the Mac.
3. On Windows: install/start TigerVNC server with a password.
4. On the Mac: add the Windows PC (its IP) → Connect → enter password → confirm
   you can see and control Windows.

- [ ] **Step 6: Commit**

```bash
cd remote
git add src/deskbridge/app.py README.md
git commit -m "feat: add entry point and README; complete v1 LAN"
```

---

## Self-Review Notes

- **Spec coverage:** both-direction control (host+controller roles, Tasks 5–8);
  saved connections (Task 3); one-click connect launching native viewer (Tasks 5,7);
  host setup wizard (Tasks 6–7); reachability vs. server-down distinction (Tasks 4,7);
  Tailscale resolution seam present (`resolve_address` use_tailscale flag, Task 4)
  with full integration deferred to v2 per spec. LAN-only v1 scope matches the spec.
- **Placeholders:** none — every code step contains complete code; manual-test
  steps name exact actions and expected results.
- **Type consistency:** `Connection(name, host, port, tailscale_name, notes)` used
  identically across Tasks 3, 4, 7; `resolve_address(conn, use_tailscale)`,
  `is_port_open(host, port, timeout)`, `build_viewer_command(os_name, address, port,
  tigervnc_path)` / `launch_viewer(...)`, `setup_instructions(os_name)` /
  `is_server_running(port)`, `current_os()` are consistent between definition and use.
