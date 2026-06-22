# v2 Tailscale (Internet) Support — Design Spec

**Date:** 2026-06-23
**Project folder:** `remote/`
**Builds on:** DeskBridge v1 (LAN remote desktop) + viewer-quality feature

## 1. Goal

Let DeskBridge control a machine across the internet (different networks) without
port forwarding, by going over a **Tailscale** mesh VPN. Tailscale gives each
machine a stable `100.x.x.x` address reachable anywhere and encrypts traffic
end-to-end, so the existing connect/viewer flow works unchanged — it just gets a
Tailscale address instead of a LAN IP.

### Success criteria

- DeskBridge shows this machine's Tailscale name + IP in the header (or
  "not installed").
- A **"Use Tailscale"** toggle switches the machine list to the **live tailnet
  peers** (auto-discovered via `tailscale status`), with online/offline marks.
- In Tailscale mode, **Connect** opens the viewer against the selected peer's
  Tailscale IP, reusing the existing reachability check and quality preset.
- If Tailscale is not installed when toggled on, the user gets an install prompt
  and the toggle reverts.

### Non-goals (YAGNI)

- No managing the tailnet from the app (no login, no ACLs, no MagicDNS config).
- No auto-install of Tailscale.
- No saving tailnet peers to the connections file — they are read live each time.

## 2. Components

### 2a. New module `src/deskbridge/tailscale.py`

Wraps the Tailscale CLI. Standard library only (`subprocess`, `json`, `os`,
`shutil`).

- `TailnetMachine` dataclass: `name: str`, `address: str`, `online: bool`.
- `tailscale_cli_path() -> str | None` — return the CLI path: the macOS app binary
  `/Applications/Tailscale.app/Contents/MacOS/Tailscale` if it exists, else
  `shutil.which("tailscale")`, else `None`.
- `is_installed() -> bool` — `tailscale_cli_path() is not None`.
- `_run_status_json(cli_path) -> dict | None` — run `<cli> status --json`, parse
  JSON; return `None` on non-zero exit, timeout, or parse error.
- `parse_status(data: dict) -> tuple[TailnetMachine | None, list[TailnetMachine]]`
  — **pure**. From parsed `tailscale status --json`, return
  `(self_machine, peers)`. For each node use `HostName` (fallback `DNSName`
  trimmed at the first dot) as `name`, `TailscaleIPs[0]` as `address`, and
  `Online` as `online`. `Self` → self_machine; each value of `Peer` → a peer.
  Peers with no `TailscaleIPs` are skipped.
- `self_machine() -> TailnetMachine | None` and `peers() -> list[TailnetMachine]`
  — convenience wrappers: locate CLI, run status, parse; return `None`/`[]` when
  Tailscale is unavailable.

### 2b. `gui.py` (modify)

- **Header:** add a second label showing `Tailscale: <name> (<ip>)` when
  `self_machine()` is available, else `Tailscale: not installed`.
- **Toolbar:** add a `tk.Checkbutton` bound to `self.use_tailscale` (BooleanVar),
  command `self._toggle_tailscale`.
- `_toggle_tailscale`:
  - turning **on** while `not is_installed()` → `messagebox.showinfo` with install
    guidance (`brew install --cask tailscale` / https://tailscale.com/download),
    reset the var to `False`, return.
  - otherwise refresh the list for the current mode.
- **List source depends on mode** (`self.use_tailscale.get()`):
  - off → saved `Connection`s (today's behavior).
  - on → `peers()`, rows rendered as `name — address (online/offline)`.
  - `_refresh_list` branches on mode; the listbox index maps to either
    `self.connections[i]` or `self._tailnet[i]` (the cached peer list).
- **connect():** branch on mode.
  - LAN mode: unchanged (`resolve_address(conn, use_tailscale=False)`,
    `conn.port`, `conn.quality`).
  - Tailscale mode: use the selected peer's `address`, port `5900`, and the
    current quality from the dropdown; same reachability check + `launch_viewer`.
- Add/Remove/Quality apply to **saved connections only** and are inert (no-op with
  a status hint) while in Tailscale mode, since tailnet peers are live, not saved.

## 3. Data flow (connect over internet)

1. User installs + logs into Tailscale on both machines (one-time, in Tailscale's
   own app).
2. User flips **Use Tailscale** on → DeskBridge lists live tailnet peers.
3. User selects a peer and clicks **Connect**.
4. DeskBridge reachability-checks the peer's `100.x` address on port 5900, then
   launches the viewer (TigerVNC + quality preset) against it. Tailscale carries
   the traffic, encrypted, across networks.

## 4. Error handling

- Tailscale not installed → header says "not installed"; toggling on shows the
  install prompt and reverts.
- Installed but not running / not logged in → `status()` returns `None`; toggling
  on shows "Tailscale isn't running or you're not logged in" and reverts.
- No peers → empty list with a status hint ("No other machines on your tailnet").
- Selected peer offline / unreachable → existing "Unreachable" warning (the
  reachability check covers it).

## 5. Testing

- `test_tailscale.py`:
  - `parse_status(sample)` returns the expected self machine and peers (names from
    `HostName`, address from `TailscaleIPs[0]`, online flags); peers without IPs
    are skipped. Uses an inline sample mimicking `tailscale status --json`.
  - `tailscale_cli_path()` returns the app path when `os.path.exists` is True
    (mocked); falls back to `shutil.which`; returns `None` when both miss.
  - `_run_status_json` returns `None` on non-zero exit / bad JSON (mocked
    `subprocess.run`).
- GUI verified by headless construct (Tailscale absent → "not installed", toggle
  reverts) and manual smoke test on a real tailnet.

## 6. Setup note (documentation)

README v2 section updated: install Tailscale and log in with the **same account**
on both Mac and Windows, then flip "Use Tailscale" in DeskBridge. Encryption and
NAT traversal are handled entirely by Tailscale.
