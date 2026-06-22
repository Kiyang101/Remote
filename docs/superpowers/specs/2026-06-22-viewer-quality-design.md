# Tunable Viewer + Quality Presets — Design Spec

**Date:** 2026-06-22
**Project folder:** `remote/`
**Builds on:** DeskBridge v1 (LAN remote desktop connection manager)

## 1. Goal

Make the macOS→Windows desktop VNC experience smooth and the cursor accurate.

Root cause (confirmed by debugging): launching the macOS built-in Screen Sharing
client via `open vnc://…` gives a degraded "standard connection" to non-Apple VNC
servers (Windows TigerVNC) — laggy, freeze-then-jump under motion. Connecting with
the **TigerVNC viewer** instead is smooth. This feature makes DeskBridge launch the
TigerVNC viewer with tuned encoding flags, exposed as simple quality presets, and
fixes the cursor-offset issue.

Note: this is for *desktop control*. Gaming/60fps is out of scope and handled by
Moonlight + Sunshine (documented in the README), not VNC.

### Success criteria

- On macOS, when TigerVNC is installed, **Connect** launches the TigerVNC viewer
  (`vncviewer`) with quality flags — not `open vnc://`.
- If TigerVNC is not installed on macOS, Connect falls back to `open vnc://` so
  nothing breaks.
- Each saved machine has a **quality** preset (Fast / Balanced / Sharp), default
  Balanced, persisted across runs and backward-compatible with existing saved JSON.
- The cursor maps 1:1 (no offset) via `RemoteResize`.

### Non-goals (YAGNI)

- No arbitrary/custom flag editor — only the three presets.
- No changes to the host (server) setup flow.
- No gaming/video-codec protocol (that is Moonlight + Sunshine, out of scope).

## 2. Components

### 2a. `viewer_launch.py` (modify)

Add a pure preset→flags mapping, a macOS TigerVNC locator, and route the macOS
command through TigerVNC when available.

- `quality_flags(quality: str) -> list[str]` — pure. Maps a preset name to
  TigerVNC parameters. Raises `ValueError` on an unknown preset. All presets
  include the common flags `-RemoteResize=1` (1:1 mapping → fixes cursor offset)
  and `-AlwaysCursor=1` (cursor always visible).

  | Preset | Preset-specific flags |
  |---|---|
  | `fast` | `-PreferredEncoding=Tight -QualityLevel=4 -CompressLevel=6 -FullColor=0 -LowColorLevel=1` |
  | `balanced` | `-PreferredEncoding=Tight -QualityLevel=7 -CompressLevel=2 -FullColor=1` |
  | `sharp` | `-PreferredEncoding=Tight -QualityLevel=9 -CompressLevel=1 -FullColor=1` |

- `macos_tigervnc_path() -> str | None` — returns
  `/Applications/TigerVNC.app/Contents/MacOS/vncviewer` if it exists, else `None`.
  (Filesystem check isolated here so the command builder stays pure/testable.)

- `build_viewer_command(os_name, address, port=5900, quality="balanced",
  tigervnc_path=None) -> list[str]` — pure. Behavior:
  - **macos** with a `tigervnc_path` → `[tigervnc_path, f"{address}::{port}", *quality_flags(quality)]`
  - **macos** without a `tigervnc_path` → `["open", f"vnc://{address}:{port}"]` (fallback; no flags — the built-in client ignores them)
  - **windows** → `[tigervnc_path or "vncviewer.exe", f"{address}::{port}", *quality_flags(quality)]`
  - other OS → `ValueError`

- `launch_viewer(os_name, address, port=5900, quality="balanced", tigervnc_path=None)`
  — for macOS, resolve `tigervnc_path = tigervnc_path or macos_tigervnc_path()`
  before building the command, then `subprocess.Popen` it.

### 2b. `connections.py` (modify)

- Add field `quality: str = "balanced"` to the `Connection` dataclass.
- `load_connections` must tolerate existing JSON entries that lack the `quality`
  key (they get the default). Current loader uses `Connection(**item)`; since the
  only stored keys are model fields and `quality` has a default, missing-key
  entries load fine. (No migration code needed.)

### 2c. `gui.py` (modify)

- Add a **Quality** dropdown (`tk.OptionMenu`) to the toolbar with values
  `Fast`, `Balanced`, `Sharp`.
- When a machine is selected in the list, the dropdown reflects that machine's
  `quality`. Changing the dropdown updates the selected machine's `quality` and
  saves immediately.
- `connect()` passes the selected machine's `quality` (lower-cased) to
  `launch_viewer`.

## 3. Data flow (Connect)

1. User selects a machine and a quality preset.
2. `connect()` resolves the address (existing logic) and reachability-checks it.
3. `launch_viewer(os_name, address, port, quality)` resolves the TigerVNC path on
   macOS, builds the command (TigerVNC + flags, or `open vnc://` fallback), and
   launches it.

## 4. Error handling

- Unknown quality string → `quality_flags` raises `ValueError` (guards against a
  bad/hand-edited config); GUI only ever passes the three known presets.
- TigerVNC missing on macOS → silent, safe fallback to `open vnc://`.
- Existing behavior (Unreachable warning, etc.) unchanged.

## 5. Testing

- `test_viewer_launch.py` (extend):
  - `quality_flags("balanced"/"fast"/"sharp")` returns the exact expected lists
    (including the common `RemoteResize`/`AlwaysCursor` flags); unknown → `ValueError`.
  - `build_viewer_command("macos", …, tigervnc_path="/path/vncviewer")` includes
    the TigerVNC binary, `address::port`, and quality flags.
  - `build_viewer_command("macos", …, tigervnc_path=None)` returns the
    `open vnc://…` fallback.
  - `build_viewer_command("windows", …)` includes `vncviewer.exe` + flags.
  - `macos_tigervnc_path()` returns the path when `os.path.exists` is True
    (mocked) and `None` when False.
- `test_connections.py` (extend):
  - `quality` defaults to `"balanced"`; round-trips through save/load.
  - Loading a JSON entry without a `quality` key yields the default.
- GUI change verified by `python -c "import deskbridge.gui"` and manual smoke test.
