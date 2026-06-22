# Check My Local IP — Design Spec

**Date:** 2026-06-22
**Project folder:** `remote/`
**Builds on:** DeskBridge v1 (LAN remote desktop connection manager)

## 1. Goal

When a machine is acting as the **host** (sharing its screen), the user needs to
know which IP address to give the controlling machine. Today the app only tells
them to run `ipconfig` or read the macOS Sharing pane. This feature surfaces the
machine's own LAN IP directly in the app.

### Success criteria

- The main window shows this machine's primary LAN IPv4 address.
- The **Share my screen** dialog states the exact address other machines should
  connect to.
- Works on both macOS and Windows without third-party dependencies.
- If there is no network, the app shows "unavailable" instead of crashing.

### Non-goals (YAGNI)

- No listing of every network interface.
- No IPv6.
- No public/internet IP lookup (the planned Tailscale path covers internet use).

## 2. Component

**New module `src/deskbridge/localip.py`** with one function:

- `local_ip() -> str | None` — returns the machine's primary LAN IPv4 address, or
  `None` if it cannot be determined.

### How it works

Uses the standard "no-traffic" routing trick: open a UDP socket and `connect()`
it to a public address (`8.8.8.8:80`). UDP `connect()` sets the socket's
destination without sending any packets; the OS then assigns the local interface
it *would* route through, which `getsockname()[0]` reads back as the real LAN IP.
This is more reliable cross-platform than `gethostbyname(gethostname())`, which
often returns `127.0.0.1` on macOS. On any `OSError` (no network), return `None`.

This module is independent: it depends only on the standard library `socket`.

## 3. GUI wiring (`src/deskbridge/gui.py`)

Two touch points, using `local_ip()`:

1. **Header label** — change the existing `This machine: <os>` label to
   `This machine: <os> · IP: <ip>`, where `<ip>` is `local_ip()` or the literal
   `unavailable` when it returns `None`. Compute it once at window construction.
2. **"Share my screen" dialog** — prepend a line to the existing message:
   `Other machines connect to this machine at: <ip>` (or `unavailable`), followed
   by a blank line and the current per-OS setup steps.

No other behavior changes.

## 4. Data flow

- At window construction: call `local_ip()` once, store the result, render it in
  the header.
- On **Share my screen** click: reuse the stored IP (or recompute) and include it
  in the dialog text alongside `setup_instructions(os_name)`.

## 5. Error handling

- `local_ip()` returns `None` on failure; the GUI renders `unavailable`. No
  exceptions propagate to the user.

## 6. Testing

- `test_localip.py`:
  - `local_ip()` returns the address from a mocked socket's `getsockname()`.
  - `local_ip()` returns `None` when `socket.socket`/`connect` raises `OSError`.
- GUI change verified by `python -c "import deskbridge.gui"` and manual smoke
  test (header shows an IP; Share-my-screen dialog shows the connect-at line).
