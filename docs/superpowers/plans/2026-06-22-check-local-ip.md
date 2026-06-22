# Check My Local IP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show this machine's primary LAN IPv4 address in the DeskBridge window and in the "Share my screen" dialog, so a host knows what address to give the controller.

**Architecture:** A new standalone `localip` module computes the primary LAN IP using a no-traffic UDP socket trick. `gui.py` uses it in the header label and the Share-my-screen dialog. No other behavior changes.

**Tech Stack:** Python 3 standard library (`socket`), Tkinter, pytest.

---

## File Structure

```
remote/src/deskbridge/localip.py   # new: local_ip() -> str | None
remote/src/deskbridge/gui.py       # modify: header label + share dialog
remote/tests/test_localip.py       # new: unit tests for local_ip()
```

---

### Task 1: `local_ip()` module (TDD)

**Files:**
- Create: `remote/src/deskbridge/localip.py`
- Test: `remote/tests/test_localip.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_localip.py
from unittest import mock

from deskbridge.localip import local_ip


def test_local_ip_returns_getsockname_address():
    fake_sock = mock.MagicMock()
    fake_sock.getsockname.return_value = ("192.168.1.42", 54321)
    fake_sock.__enter__.return_value = fake_sock
    with mock.patch("socket.socket", return_value=fake_sock):
        assert local_ip() == "192.168.1.42"
    fake_sock.connect.assert_called_once_with(("8.8.8.8", 80))


def test_local_ip_returns_none_on_oserror():
    with mock.patch("socket.socket", side_effect=OSError):
        assert local_ip() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd remote && python -m pytest tests/test_localip.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deskbridge.localip'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/deskbridge/localip.py
"""Determine this machine's primary LAN IPv4 address."""

import socket


def local_ip() -> str | None:
    """Return this machine's primary LAN IPv4 address, or None if unavailable.

    Uses a UDP socket "connected" to a public address: no packets are sent, but
    the OS assigns the local interface it would route through, which
    getsockname() reports as the real LAN IP. More reliable cross-platform than
    gethostbyname(gethostname()), which often returns 127.0.0.1 on macOS.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd remote && python -m pytest tests/test_localip.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
cd remote
git add src/deskbridge/localip.py tests/test_localip.py
git commit -m "feat: add local_ip() to detect primary LAN address"
```

---

### Task 2: Wire local IP into the GUI

**Files:**
- Modify: `remote/src/deskbridge/gui.py`

Context: `gui.py` defines `class DeskBridgeApp`. Its `__init__` builds a header
label `tk.Label(root, text=f"This machine: {self.os_name}")` and a `share_screen`
method that shows `setup_instructions(self.os_name)` in a messagebox. We add the
local IP to both.

- [ ] **Step 1: Import local_ip**

In `gui.py`, add to the imports block (next to the other `from deskbridge...` imports):

```python
from deskbridge.localip import local_ip
```

- [ ] **Step 2: Compute and show the IP in the header**

In `DeskBridgeApp.__init__`, after `self.os_name = current_os()`, add:

```python
        self.local_ip = local_ip() or "unavailable"
```

Then change the header label line from:

```python
        tk.Label(root, text=f"This machine: {self.os_name}").pack(anchor="w", padx=8, pady=4)
```

to:

```python
        tk.Label(
            root, text=f"This machine: {self.os_name} · IP: {self.local_ip}"
        ).pack(anchor="w", padx=8, pady=4)
```

- [ ] **Step 3: Include the connect-at address in the Share-my-screen dialog**

Change the `share_screen` method from:

```python
    def share_screen(self):
        running = is_server_running()
        steps = setup_instructions(self.os_name)
        prefix = "VNC server appears to be running.\n\n" if running else ""
        messagebox.showinfo("Share my screen", prefix + steps)
```

to:

```python
    def share_screen(self):
        running = is_server_running()
        steps = setup_instructions(self.os_name)
        address_line = f"Other machines connect to this machine at: {self.local_ip}\n\n"
        prefix = "VNC server appears to be running.\n\n" if running else ""
        messagebox.showinfo("Share my screen", address_line + prefix + steps)
```

- [ ] **Step 4: Verify the GUI module still imports and tests pass**

Run: `cd remote && python -c "import deskbridge.gui" && python -m pytest -q`
Expected: import succeeds (exit 0) and the full suite passes (21 passed).

- [ ] **Step 5: Manual smoke test (display required — note if not possible)**

Run: `cd remote && deskbridge`
Expected: header reads `This machine: macos · IP: <your LAN IP>`; clicking
**Share my screen** shows a dialog whose first line is
`Other machines connect to this machine at: <your LAN IP>`.
If no display is available in the environment, skip and note it.

- [ ] **Step 6: Commit**

```bash
cd remote
git add src/deskbridge/gui.py
git commit -m "feat: show local IP in header and share-screen dialog"
```

---

## Self-Review Notes

- **Spec coverage:** primary LAN IPv4 via no-traffic UDP trick (Task 1);
  `None`→`unavailable` handling (Task 1 + GUI fallback); header display and
  Share-my-screen connect-at line (Task 2). Non-goals (interfaces/IPv6/public IP)
  excluded.
- **Placeholders:** none — complete code in every step.
- **Type consistency:** `local_ip() -> str | None` defined in Task 1 and consumed
  in Task 2 with `or "unavailable"`; `self.local_ip` set in `__init__` and reused
  in `share_screen`.
