# v2 Tailscale (Internet) Support — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add a `tailscale` module that reads the tailnet via the Tailscale CLI, and a GUI "Use Tailscale" toggle that lists live tailnet peers and connects to them over the internet — reusing the existing reachability/viewer/quality path.

**Architecture:** `tailscale.py` locates the CLI, runs `tailscale status --json`, and parses it (pure `parse_status`) into a self machine + peers. The GUI gains a Tailscale header line and a toggle that swaps the list source between saved LAN connections and live peers; connect branches on the mode.

**Tech Stack:** Python 3 stdlib (`subprocess`, `json`, `os`, `shutil`), Tkinter, pytest.

---

## File Structure

```
remote/src/deskbridge/tailscale.py   # new: CLI wrapper + parse_status
remote/src/deskbridge/gui.py         # modify: header line, toggle, list/connect branch
remote/tests/test_tailscale.py       # new: parsing, cli detection, status errors
remote/README.md                     # modify: v2 setup section
```

---

### Task 1: `tailscale` module (TDD)

**Files:**
- Create: `remote/src/deskbridge/tailscale.py`
- Test: `remote/tests/test_tailscale.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tailscale.py
from unittest import mock

from deskbridge import tailscale as ts
from deskbridge.tailscale import TailnetMachine, parse_status

SAMPLE = {
    "Self": {
        "HostName": "my-mac",
        "DNSName": "my-mac.tailnet.ts.net.",
        "TailscaleIPs": ["100.64.0.1"],
        "Online": True,
    },
    "Peer": {
        "nodekey:abc": {
            "HostName": "my-windows",
            "DNSName": "my-windows.tailnet.ts.net.",
            "TailscaleIPs": ["100.64.0.2"],
            "Online": True,
        },
        "nodekey:def": {
            "HostName": "old-laptop",
            "DNSName": "old-laptop.tailnet.ts.net.",
            "TailscaleIPs": [],
            "Online": False,
        },
    },
}


def test_parse_status_self_and_peers():
    self_m, peers = parse_status(SAMPLE)
    assert self_m == TailnetMachine("my-mac", "100.64.0.1", True)
    # old-laptop has no IP and is skipped
    assert peers == [TailnetMachine("my-windows", "100.64.0.2", True)]


def test_parse_status_empty():
    self_m, peers = parse_status({})
    assert self_m is None
    assert peers == []


def test_cli_path_prefers_macos_app():
    with mock.patch("os.path.exists", return_value=True):
        assert ts.tailscale_cli_path() == ts.MACOS_APP_CLI


def test_cli_path_falls_back_to_which():
    with mock.patch("os.path.exists", return_value=False), \
         mock.patch("shutil.which", return_value="/usr/bin/tailscale"):
        assert ts.tailscale_cli_path() == "/usr/bin/tailscale"


def test_cli_path_none_when_absent():
    with mock.patch("os.path.exists", return_value=False), \
         mock.patch("shutil.which", return_value=None):
        assert ts.tailscale_cli_path() is None
        assert ts.is_installed() is False


def test_run_status_json_ok():
    completed = mock.Mock(returncode=0, stdout='{"Self": {}}')
    with mock.patch("subprocess.run", return_value=completed):
        assert ts._run_status_json("tailscale") == {"Self": {}}


def test_run_status_json_nonzero_returns_none():
    completed = mock.Mock(returncode=1, stdout="")
    with mock.patch("subprocess.run", return_value=completed):
        assert ts._run_status_json("tailscale") is None


def test_run_status_json_bad_json_returns_none():
    completed = mock.Mock(returncode=0, stdout="not json")
    with mock.patch("subprocess.run", return_value=completed):
        assert ts._run_status_json("tailscale") is None


def test_run_status_json_oserror_returns_none():
    with mock.patch("subprocess.run", side_effect=OSError):
        assert ts._run_status_json("tailscale") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd remote && python3 -m pytest tests/test_tailscale.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'deskbridge.tailscale'`.

- [ ] **Step 3: Write the implementation**

```python
# src/deskbridge/tailscale.py
"""Read the local tailnet via the Tailscale CLI."""

import json
import os
import shutil
import subprocess
from dataclasses import dataclass

MACOS_APP_CLI = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"


@dataclass
class TailnetMachine:
    name: str
    address: str
    online: bool


def tailscale_cli_path() -> str | None:
    """Locate the Tailscale CLI: macOS app binary, then PATH, else None."""
    if os.path.exists(MACOS_APP_CLI):
        return MACOS_APP_CLI
    return shutil.which("tailscale")


def is_installed() -> bool:
    return tailscale_cli_path() is not None


def _machine_from_node(node: dict) -> TailnetMachine | None:
    ips = node.get("TailscaleIPs") or []
    if not ips:
        return None
    name = node.get("HostName") or (node.get("DNSName") or "").split(".")[0]
    return TailnetMachine(
        name=name or "unknown",
        address=ips[0],
        online=bool(node.get("Online", False)),
    )


def parse_status(data: dict) -> tuple[TailnetMachine | None, list[TailnetMachine]]:
    """From `tailscale status --json`, return (self_machine, peers).

    Nodes without a Tailscale IP are skipped.
    """
    self_node = data.get("Self")
    self_machine = _machine_from_node(self_node) if self_node else None
    peers = []
    for node in (data.get("Peer") or {}).values():
        machine = _machine_from_node(node)
        if machine:
            peers.append(machine)
    return self_machine, peers


def _run_status_json(cli_path: str) -> dict | None:
    try:
        result = subprocess.run(
            [cli_path, "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except ValueError:
        return None


def _status() -> dict | None:
    cli = tailscale_cli_path()
    if cli is None:
        return None
    return _run_status_json(cli)


def self_machine() -> TailnetMachine | None:
    data = _status()
    return parse_status(data)[0] if data is not None else None


def peers() -> list[TailnetMachine]:
    data = _status()
    return parse_status(data)[1] if data is not None else []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd remote && python3 -m pytest tests/test_tailscale.py -v`
Expected: PASS (all tailscale tests green).

- [ ] **Step 5: Commit**

```bash
cd remote
git add src/deskbridge/tailscale.py tests/test_tailscale.py
git commit -m "feat: add tailscale module to read tailnet machines"
```

---

### Task 2: GUI Tailscale toggle + header

**Files:**
- Modify: `remote/src/deskbridge/gui.py`

Behavior to implement (full edits applied in implementation):

1. **Imports:** add
   `from deskbridge.tailscale import is_installed as tailscale_is_installed, peers as tailscale_peers, self_machine as tailscale_self_machine`.
2. **Early init (before first `_refresh_list`):** set
   `self.use_tailscale = tk.BooleanVar(value=False)` and `self._tailnet = []`.
3. **Header:** add a label `Tailscale: <name> (<ip>)` from `tailscale_self_machine()`,
   or `Tailscale: not installed`.
4. **Toolbar:** add `tk.Checkbutton(text="Use Tailscale", variable=self.use_tailscale,
   command=self._toggle_tailscale)`.
5. **`_toggle_tailscale`:** when turning on and `not tailscale_is_installed()`,
   show an install messagebox (`brew install --cask tailscale` /
   https://tailscale.com/download), reset the var to False, return. Otherwise
   `_refresh_list()` and set a status hint (peers found / none / LAN mode).
6. **`_refresh_list`:** branch on `self.use_tailscale.get()` — Tailscale mode caches
   `self._tailnet = tailscale_peers()` and lists `name — address (online/offline)`;
   LAN mode lists saved connections as before.
7. **`connect`:** branch — Tailscale mode uses the selected peer's `address`, port
   `5900`, and the current dropdown quality; LAN mode unchanged. Shared reachability
   check + `launch_viewer`.
8. **`_on_select` / `_on_quality_change`:** no-op in Tailscale mode (peers have no
   quality field).
9. **`add_machine` / `remove_machine`:** no-op with a status hint in Tailscale mode
   ("Switch off Tailscale to edit saved machines.").

- [ ] **Step 1: Apply the edits above to `gui.py`.**

- [ ] **Step 2: Verify imports + full suite**

Run: `cd remote && python3 -c "import deskbridge.gui" && python3 -m pytest -q`
Expected: import OK; full suite green.

- [ ] **Step 3: Headless GUI construct test**

Construct `DeskBridgeApp` with a withdrawn root and Tailscale absent; assert the
header shows "not installed" and that flipping `use_tailscale` on reverts to False
(install prompt path). Destroy the root. Expected: passes without error.

- [ ] **Step 4: Commit**

```bash
cd remote
git add src/deskbridge/gui.py
git commit -m "feat: add Use Tailscale toggle and tailnet machine list to GUI"
```

---

### Task 3: README v2 section

**Files:**
- Modify: `remote/README.md`

- [ ] **Step 1: Replace the "Using it over the internet (v2 — planned)" section**
with a shipped v2 section: install Tailscale + log in with the **same account** on
both Mac and Windows, flip **Use Tailscale** in DeskBridge, pick the machine, Connect.
Note encryption + NAT traversal are handled by Tailscale.

- [ ] **Step 2: Commit**

```bash
cd remote
git add README.md
git commit -m "docs: document shipped v2 Tailscale internet support"
```

---

## Self-Review Notes

- **Spec coverage:** CLI detection + status parse (Task 1); header line, toggle,
  live peer list, internet connect reusing reachability/viewer/quality (Task 2);
  not-installed/not-running handling (Tasks 1–2); docs (Task 3). Non-goals
  (login/ACL/MagicDNS/auto-install/peer-saving) excluded.
- **Placeholders:** none in the testable module; GUI behavior fully specified.
- **Type consistency:** `TailnetMachine(name, address, online)`, `parse_status ->
  (TailnetMachine | None, list[TailnetMachine])`, `peers() -> list[TailnetMachine]`,
  `self_machine() -> TailnetMachine | None`, `is_installed() -> bool` are used
  consistently across module and GUI.
