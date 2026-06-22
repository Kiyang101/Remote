# Tunable Viewer + Quality Presets — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make DeskBridge launch the TigerVNC viewer (with tuned encoding flags exposed as Fast/Balanced/Sharp quality presets) on macOS instead of the throttled built-in `open vnc://` client, fix the cursor offset via `RemoteResize`, and persist a quality preset per saved machine.

**Architecture:** A pure `quality_flags()` mapping + a macOS TigerVNC locator drive `build_viewer_command`, which now routes macOS through TigerVNC when installed (falling back to `open vnc://` otherwise) and appends quality flags on both OSes. `Connection` gains a `quality` field; the GUI gets a quality dropdown.

**Tech Stack:** Python 3 standard library, Tkinter, pytest. No new runtime dependencies.

---

## File Structure

```
remote/src/deskbridge/connections.py     # modify: add quality field
remote/src/deskbridge/viewer_launch.py    # modify: presets, locator, command routing
remote/src/deskbridge/gui.py              # modify: quality dropdown + pass quality
remote/tests/test_connections.py          # modify: quality tests
remote/tests/test_viewer_launch.py        # modify: flags + fallback + locator tests
```

---

### Task 1: Add `quality` to the Connection model (TDD)

**Files:**
- Modify: `remote/src/deskbridge/connections.py`
- Test: `remote/tests/test_connections.py`

- [ ] **Step 1: Add the failing tests**

Append these two tests to `tests/test_connections.py`:

```python
def test_quality_defaults_to_balanced():
    c = Connection(name="x", host="h")
    assert c.quality == "balanced"


def test_quality_roundtrips_and_tolerates_legacy_json(tmp_path):
    path = tmp_path / "connections.json"
    save_connections(path, [Connection(name="A", host="h", quality="fast")])
    assert load_connections(path)[0].quality == "fast"

    # Legacy entry written before the quality field existed must still load.
    path.write_text('[{"name": "B", "host": "h2", "port": 5900, '
                    '"tailscale_name": null, "notes": ""}]')
    loaded = load_connections(path)
    assert loaded[0].name == "B"
    assert loaded[0].quality == "balanced"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd remote && python -m pytest tests/test_connections.py -v`
Expected: the two new tests FAIL (`AttributeError: 'Connection' object has no attribute 'quality'`).

- [ ] **Step 3: Add the field**

In `src/deskbridge/connections.py`, change the dataclass from:

```python
@dataclass
class Connection:
    name: str
    host: str
    port: int = 5900
    tailscale_name: str | None = None
    notes: str = ""
```

to:

```python
@dataclass
class Connection:
    name: str
    host: str
    port: int = 5900
    tailscale_name: str | None = None
    notes: str = ""
    quality: str = "balanced"
```

(No loader change needed: `quality` has a default, so legacy JSON entries without
the key construct fine via `Connection(**item)`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd remote && python -m pytest tests/test_connections.py -v`
Expected: PASS (all connection tests green).

- [ ] **Step 5: Commit**

```bash
cd remote
git add src/deskbridge/connections.py tests/test_connections.py
git commit -m "feat: add per-connection quality preset field"
```

---

### Task 2: Quality presets + TigerVNC routing in viewer_launch (TDD)

**Files:**
- Modify: `remote/src/deskbridge/viewer_launch.py`
- Test: `remote/tests/test_viewer_launch.py`

- [ ] **Step 1: Replace the test file with the updated expectations**

Overwrite `tests/test_viewer_launch.py` with:

```python
from unittest import mock

import pytest

from deskbridge.viewer_launch import (
    build_viewer_command,
    macos_tigervnc_path,
    quality_flags,
)

VNCVIEWER = "/Applications/TigerVNC.app/Contents/MacOS/vncviewer"


def test_quality_flags_balanced():
    assert quality_flags("balanced") == [
        "-RemoteResize=1",
        "-AlwaysCursor=1",
        "-PreferredEncoding=Tight",
        "-QualityLevel=7",
        "-CompressLevel=2",
        "-FullColor=1",
    ]


def test_quality_flags_fast():
    assert quality_flags("fast") == [
        "-RemoteResize=1",
        "-AlwaysCursor=1",
        "-PreferredEncoding=Tight",
        "-QualityLevel=4",
        "-CompressLevel=6",
        "-FullColor=0",
        "-LowColorLevel=1",
    ]


def test_quality_flags_sharp():
    assert quality_flags("sharp") == [
        "-RemoteResize=1",
        "-AlwaysCursor=1",
        "-PreferredEncoding=Tight",
        "-QualityLevel=9",
        "-CompressLevel=1",
        "-FullColor=1",
    ]


def test_quality_flags_unknown_raises():
    with pytest.raises(ValueError):
        quality_flags("ultra")


def test_macos_command_uses_tigervnc_when_available():
    cmd = build_viewer_command(
        "macos", "192.168.1.5", 5900, quality="balanced", tigervnc_path=VNCVIEWER
    )
    assert cmd == [VNCVIEWER, "192.168.1.5::5900", *quality_flags("balanced")]


def test_macos_command_falls_back_to_open_without_tigervnc():
    cmd = build_viewer_command("macos", "192.168.1.5", 5900, tigervnc_path=None)
    assert cmd == ["open", "vnc://192.168.1.5:5900"]


def test_windows_command_default_path_includes_flags():
    cmd = build_viewer_command("windows", "192.168.1.5", 5901, quality="fast")
    assert cmd == ["vncviewer.exe", "192.168.1.5::5901", *quality_flags("fast")]


def test_windows_command_custom_path():
    cmd = build_viewer_command(
        "windows", "host", 5900, tigervnc_path=r"C:\Tools\vncviewer.exe"
    )
    assert cmd == [r"C:\Tools\vncviewer.exe", "host::5900", *quality_flags("balanced")]


def test_unsupported_os_raises():
    with pytest.raises(ValueError):
        build_viewer_command("other", "host", 5900)


def test_macos_tigervnc_path_found():
    with mock.patch("os.path.exists", return_value=True):
        assert macos_tigervnc_path() == VNCVIEWER


def test_macos_tigervnc_path_missing():
    with mock.patch("os.path.exists", return_value=False):
        assert macos_tigervnc_path() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd remote && python -m pytest tests/test_viewer_launch.py -v`
Expected: FAIL with `ImportError: cannot import name 'quality_flags'` (and others).

- [ ] **Step 3: Rewrite the implementation**

Overwrite `src/deskbridge/viewer_launch.py` with:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd remote && python -m pytest tests/test_viewer_launch.py -v`
Expected: PASS (all viewer_launch tests green).

- [ ] **Step 5: Commit**

```bash
cd remote
git add src/deskbridge/viewer_launch.py tests/test_viewer_launch.py
git commit -m "feat: launch TigerVNC viewer with quality presets; fix cursor offset"
```

---

### Task 3: Quality dropdown in the GUI

**Files:**
- Modify: `remote/src/deskbridge/gui.py`

Context: `DeskBridgeApp.__init__` builds a `btns` frame and a `listbox`; `connect()`
calls `launch_viewer(self.os_name, address, conn.port)`. We add a quality dropdown
that reflects/edits the selected machine's `quality`, and pass it on connect.

- [ ] **Step 1: Add a quality OptionMenu and selection binding in `__init__`**

In `gui.py`, change the listbox setup from:

```python
        self.listbox = tk.Listbox(root)
        self.listbox.pack(fill="both", expand=True, padx=8, pady=4)
        self._refresh_list()
```

to:

```python
        self.listbox = tk.Listbox(root)
        self.listbox.pack(fill="both", expand=True, padx=8, pady=4)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self._refresh_list()
```

Then change the buttons frame from:

```python
        btns = tk.Frame(root)
        btns.pack(fill="x", padx=8, pady=4)
        tk.Button(btns, text="Connect", command=self.connect).pack(side="left")
        tk.Button(btns, text="Add", command=self.add_machine).pack(side="left")
        tk.Button(btns, text="Remove", command=self.remove_machine).pack(side="left")
        tk.Button(btns, text="Share my screen", command=self.share_screen).pack(side="right")
```

to:

```python
        btns = tk.Frame(root)
        btns.pack(fill="x", padx=8, pady=4)
        tk.Button(btns, text="Connect", command=self.connect).pack(side="left")
        tk.Button(btns, text="Add", command=self.add_machine).pack(side="left")
        tk.Button(btns, text="Remove", command=self.remove_machine).pack(side="left")
        self.quality_var = tk.StringVar(value="Balanced")
        tk.OptionMenu(
            btns, self.quality_var, "Fast", "Balanced", "Sharp",
            command=self._on_quality_change,
        ).pack(side="left", padx=(8, 0))
        tk.Button(btns, text="Share my screen", command=self.share_screen).pack(side="right")
```

- [ ] **Step 2: Add the selection/quality handlers**

In `gui.py`, add these two methods to `DeskBridgeApp` (e.g. right after `_selected`):

```python
    def _on_select(self, event=None):
        conn = self._selected()
        if conn:
            self.quality_var.set(conn.quality.capitalize())

    def _on_quality_change(self, value):
        conn = self._selected()
        if conn:
            conn.quality = value.lower()
            save_connections(self.config_path, self.connections)
```

- [ ] **Step 3: Pass the quality to launch_viewer in `connect`**

In `gui.py`, change:

```python
        launch_viewer(self.os_name, address, conn.port)
```

to:

```python
        launch_viewer(self.os_name, address, conn.port, quality=conn.quality)
```

- [ ] **Step 4: Verify imports and full suite**

Run: `cd remote && python -c "import deskbridge.gui" && python -m pytest -q`
Expected: import succeeds (exit 0) and the full suite passes.

- [ ] **Step 5: Manual smoke test (display required — note if not possible)**

Run: `cd remote && deskbridge`
Expected: a **Quality** dropdown (Fast/Balanced/Sharp) appears in the button row;
selecting a saved machine sets the dropdown to its saved quality; changing it and
reopening the app preserves the choice; **Connect** on macOS launches the TigerVNC
viewer (smooth, cursor aligned) when TigerVNC is installed. If no display is
available, skip and note it.

- [ ] **Step 6: Commit**

```bash
cd remote
git add src/deskbridge/gui.py
git commit -m "feat: add quality preset dropdown to the GUI"
```

---

## Self-Review Notes

- **Spec coverage:** TigerVNC routing + `open vnc://` fallback on macOS (Task 2);
  quality presets with exact flags incl. `RemoteResize` cursor fix (Task 2);
  per-connection `quality` persisted + legacy-JSON tolerance (Task 1); GUI dropdown
  reflecting/saving/using quality (Task 3). Non-goals (custom flag editor, server
  flow, gaming) excluded.
- **Placeholders:** none — full code in every step.
- **Type consistency:** `quality_flags(quality) -> list[str]`, `macos_tigervnc_path()
  -> str | None`, and `build_viewer_command(os_name, address, port, quality,
  tigervnc_path)` / `launch_viewer(...)` are defined in Task 2 and consumed
  consistently; GUI passes `quality=conn.quality` matching the new keyword arg;
  `Connection.quality` default `"balanced"` aligns with the GUI default `"Balanced"`.
