# Remote Desktop (Mac ⇄ Windows) — Design Spec

**Date:** 2026-06-22
**Project folder:** `remote/`
**Working name:** DeskBridge

## 1. Goal

A practical, two-way remote desktop tool so the user can see and control the
other machine's screen between a Mac and a Windows PC. Works on the same local
network first; works over the internet as a fast-follow. Built by *wrapping
proven components* (VNC for the screen/input transport, Tailscale for
internet/encryption) rather than re-implementing a video pipeline.

### Success criteria

- From the Mac, the user can connect to and control the Windows desktop on the LAN.
- From Windows, the user can connect to and control the Mac desktop on the LAN.
- Connecting is one action (pick a saved machine → Connect) after a one-time setup.
- A documented path makes the same flow work across the internet via Tailscale.

### Non-goals (v1)

- No custom video codec or hand-rolled screen streaming.
- No file transfer, clipboard sync, or remote audio in v1 (listed as "Later").
- Not a distributable product; this is a personal/practical tool.

## 2. Strategy: reuse vs. build

| Hard problem                         | Solved by                  | We build? |
|--------------------------------------|----------------------------|-----------|
| Screen capture + encoding            | VNC server                 | No (reuse)|
| Mouse/keyboard injection             | VNC server                 | No (reuse)|
| Rendering the remote screen          | Native VNC viewer          | No (reuse)|
| NAT traversal / internet reachability| Tailscale                  | No (reuse)|
| Encryption in transit                | Tailscale (mesh VPN)       | No (reuse)|
| Setup, connection manager, launch UX | **Our Python app**         | **Yes**   |

The program we build is the **glue and UX**: it ensures the right VNC server is
running for the current OS, stores a list of machines, and launches the correct
native viewer pointed at the chosen machine with the right address/settings.

## 3. Architecture

Each machine plays two roles so control works in both directions:

- **Host role** — runs a VNC *server* sharing its screen and accepting input.
- **Controller role** — runs a VNC *viewer* to see/control the other machine.

```
   MAC                                      WINDOWS
 +----------------+                       +----------------+
 | DeskBridge app |  -- controls -->      | VNC server     |
 | + VNC viewer   |                       | + DeskBridge   |
 | + VNC server   |     <-- controls --   | + VNC viewer   |
 +----------------+                       +----------------+
        \------- Tailscale (encrypted; LAN or internet) -------/
```

### VNC components per OS

- **macOS host:** built-in **Screen Sharing** (a real VNC server), enabled once
  in System Settings with a password.
- **macOS viewer:** built-in — the app opens `vnc://<address>` (Screen Sharing client).
- **Windows host:** bundled free server — **TigerVNC** (server), installed/configured
  with the app's help. (UltraVNC is an alternative if TigerVNC proves troublesome.)
- **Windows viewer:** bundled **TigerVNC viewer** (Windows has no built-in VNC viewer).

The app abstracts these differences so the user sees the same buttons on both platforms.

### Viewer decision: launch native (chosen)

The app launches the **native viewer** rather than embedding a hand-rendered
framebuffer in Python. This gives the smoothest picture and the least code. The
trade-off accepted: the remote screen appears in a separate viewer window, not
inside the DeskBridge window.

## 4. The program (what we build)

A small, dependency-light cross-platform app.

- **Language:** Python 3.
- **GUI:** Tkinter (standard library; no extra GUI dependency).
- **Structure (modules, each with one clear job):**
  - `platform_detect` — identify OS and capabilities.
  - `vnc_server` — check/enable/guide the OS-appropriate VNC server (mac Screen
    Sharing vs. Windows TigerVNC). Reports status; runs a setup wizard when needed.
  - `viewer_launch` — given an address, launch the correct native viewer
    (`open vnc://...` on macOS; TigerVNC viewer exe on Windows).
  - `connections` — load/save the machine list (name, address/hostname,
    Tailscale name, port, notes) to a JSON config file.
  - `net` — resolve a machine to a reachable address (LAN hostname/IP, or
    Tailscale name) and do a quick reachability check on the VNC port.
  - `gui` — Tkinter connection-manager window: list machines, Add/Edit/Remove,
    Connect, "Share my screen" (host setup), and a status line.
  - `tailscale` (v2) — detect Tailscale, surface this machine's Tailscale name,
    and link to install if missing.

### Data: connections config

A JSON file (e.g. `~/.deskbridge/connections.json`) holding a list of machines:
name, host/IP, optional Tailscale name, VNC port (default 5900), and notes. No
secrets stored in plaintext beyond what's necessary; VNC passwords are entered
in the viewer/server, not stored by the app in v1.

## 5. Data / control flow (connect to a machine)

1. User picks a saved machine in the GUI and clicks **Connect**.
2. `net` resolves it to an address (LAN IP/hostname, or Tailscale name) and
   checks the VNC port is reachable.
3. `viewer_launch` opens the native viewer for the current OS pointed at that
   address; the user authenticates with the VNC password.
4. The viewer window shows the remote desktop; input flows to the host.

"Share my screen" path:
1. User clicks **Share my screen**.
2. `vnc_server` checks whether the OS VNC server is enabled; if not, the setup
   wizard guides enabling it (mac: System Settings steps; Windows: install/start
   TigerVNC server) and setting a password.
3. App shows this machine's address(es) to hand to the other side.

## 6. Internet support (v2, via Tailscale)

Tailscale is a mesh VPN that gives each machine a stable name/IP reachable from
anywhere and encrypts traffic end-to-end. With both machines on the same
Tailscale network ("tailnet"), the *exact same* connect flow works over the
internet — no port forwarding, and VNC's weak built-in encryption stops mattering
because Tailscale wraps it. The app detects Tailscale, shows the machine's
Tailscale name, and points the user to install it if absent.

## 7. Security

- **LAN (v1):** rely on VNC server password + trusted local network. Document the
  risk that plain VNC is weakly encrypted; recommend Tailscale even on LAN.
- **Internet (v2):** Tailscale provides end-to-end encryption and access control;
  this is the recommended way to expose the desktop beyond the LAN.
- The app never disables OS security prompts or stores VNC passwords in plaintext
  config in v1.

## 8. Error handling

- VNC server not enabled on host → setup wizard with OS-specific steps.
- Target unreachable (port closed / wrong address) → clear message distinguishing
  "can't reach the machine" from "VNC server not running."
- No native viewer found on Windows → prompt to install/locate the bundled TigerVNC viewer.
- Tailscale referenced but not installed → link to install, fall back to LAN address.

## 9. Testing

- **Unit:** `connections` (load/save/round-trip JSON), `net` address resolution and
  reachability check (mockable), `platform_detect`, `viewer_launch` command
  construction per OS (assert the right command/args without actually launching).
- **Integration (manual checklist):** enable mac Screen Sharing → connect from
  Windows; install/start Windows TigerVNC → connect from Mac; both on Tailscale →
  connect across networks.
- GUI verified manually against the connection-manager checklist.

## 10. Build phases

- **v1 (LAN):** modules above, Tkinter GUI, saved connections, one-click connect
  launching the native viewer, host setup wizard. Manual one-time VNC-server enable.
- **v2 (Internet):** Tailscale detection + integration so the same flow works across networks.
- **Later (only if wanted):** file transfer, clipboard sync, embedded viewer option.

## 11. Open assumptions to confirm

- Working name "DeskBridge" is a placeholder; project folder is `remote/`.
- TigerVNC chosen for Windows (server + viewer); UltraVNC is the fallback if needed.
- Tkinter is acceptable for the GUI (no heavier framework in v1).
