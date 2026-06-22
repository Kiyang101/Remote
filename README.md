# DeskBridge

Two-way remote desktop between a Mac and a Windows PC. DeskBridge is the
**connection manager** — it remembers your machines, checks they're reachable,
and launches the right VNC viewer. The actual screen sharing is done by each
OS's VNC **server** (macOS Screen Sharing / Windows TigerVNC) and the native
VNC **viewer**.

Each machine can act as both:
- **Host** — shares its screen so the other machine can control it.
- **Controller** — views and controls the other machine.

---

## 1. Install

Do this on **both** machines (Mac and Windows). Requires Python 3.10+; no
third-party runtime dependencies.

```
cd remote
pip install -e .
```

This installs a `deskbridge` command.

## 2. Run

```
deskbridge
```

(or `python -m deskbridge.app`)

A small window opens showing **"This machine: macos · IP: 192.168.1.x"** (or
**windows**) — that IP is this machine's LAN address, which you hand to the other
machine when sharing your screen. Below it are a list of saved machines and the
buttons **Connect · Add · Remove · Share my screen**.

---

## 3. Set up the machine you want to control (the Host)

Do this once on whichever machine will be controlled. In the app, click
**Share my screen** to see these exact steps for your OS:

### macOS host
1. System Settings → General → **Sharing** → turn on **Screen Sharing**.
2. Click the (i) → **Computer Settings…** → tick *"VNC viewers may control
   screen with password"* and set a password.
3. Note the Mac's name/IP shown in the Sharing pane.

### Windows host
1. Install **TigerVNC** for Windows (https://tigervnc.org) and run the installer.
2. Start **TigerVNC Server** and set a connection password.
3. Allow it through Windows Firewall on the private network when prompted.

> Tip: the IP to give the other machine is shown in DeskBridge's header and at
> the top of the **Share my screen** dialog — no need to run `ipconfig`.

> DeskBridge never changes these OS security settings for you — it only shows
> the steps. You enable the server and set the password yourself.

---

## 4. Connect from the other machine (the Controller)

On the machine you're sitting at:

1. Click **Add** → enter a **Name** (e.g. "My Windows PC") and the host's
   **IP or hostname** (e.g. `192.168.1.42` or `my-mac.local`). It's saved to
   `~/.deskbridge/connections.json` so you only add it once.
2. Select the machine in the list and click **Connect**.
3. DeskBridge checks the host is reachable, then opens the native VNC viewer.
   Enter the VNC password you set on the host.
4. You're now seeing and controlling the other desktop.

**Viewers — use TigerVNC for a smooth picture.** macOS's built-in Screen Sharing
client throttles connections to non-Apple VNC servers (laggy, freeze-then-jump),
so DeskBridge prefers the **TigerVNC viewer** when it's installed:

- **macOS:** `brew install --cask tigervnc`. DeskBridge auto-detects it and
  launches it with tuned settings. If it's not installed, DeskBridge falls back
  to the built-in `vnc://` client (lower quality).
- **Windows:** install the TigerVNC **viewer**; if `vncviewer.exe` isn't on your
  PATH, the launch command can be pointed at its full path.

**Quality dropdown.** Pick a preset per machine in the toolbar:
- **Fast** — smoothest motion, lower image quality (slow links).
- **Balanced** — the default.
- **Sharp** — best image, more bandwidth.

The presets also map the remote 1:1, which fixes the cursor-offset issue.

Because both machines can host *and* control, repeat steps 3–4 in the other
direction to control the first machine.

---

## 5. Everyday use

1. Open `deskbridge` on the machine you're at.
2. Pick the machine from the list → **Connect** → enter password.

If you see an **"Unreachable"** warning, the other machine is off, not on the
same network, or its VNC server isn't running — turn the server on (step 3) and
check the IP.

---

## Using it over the internet (Tailscale)

DeskBridge can control a machine on a **different network** (across the internet)
by going over **Tailscale**, a free mesh VPN that handles NAT traversal and
encrypts traffic end-to-end — no port forwarding, and VNC's weak built-in
encryption stops mattering.

**One-time setup (both machines):**
1. Install Tailscale and **log in with the same account** on the Mac and Windows:
   - macOS: `brew install --cask tailscale` (or https://tailscale.com/download)
   - Windows: https://tailscale.com/download
2. Confirm both show up in your tailnet.

**Connecting:**
1. In DeskBridge, tick **Use Tailscale (internet)**. The list switches to the
   machines currently on your tailnet (with online/offline marks). The header
   shows this machine's own Tailscale name/IP.
2. Select the machine and click **Connect** — it connects to that machine's
   Tailscale address (`100.x.x.x`) using the same viewer + quality preset.

The host still needs its VNC server running (Screen Sharing / TigerVNC) as in the
LAN setup. Add/Remove and saved-machine editing apply to LAN mode; tailnet
machines are read live, so there's nothing to save.

---

## Gaming / high frame rate — use Moonlight + Sunshine, not VNC

DeskBridge (VNC) is built for **desktop control** — files, admin, coding. VNC's
protocol sends changed pixel regions on demand, so it cannot deliver smooth,
locked 60 fps, and it is the wrong tool for games or full-motion video.

For 60 fps low-latency streaming (e.g. playing Windows games on the Mac), use a
hardware-encoded video protocol instead:

- **Sunshine** on the Windows PC (host) — captures and GPU-encodes the screen.
  Install from https://github.com/LizardByte/Sunshine/releases.
- **Moonlight** on the Mac (client) — `brew install --cask moonlight`. Pair with
  the PIN Sunshine shows, then stream at 60 fps / HEVC.

Moonlight also captures the mouse properly (relative mode for games), so it does
not have VNC's cursor-offset issues. Keep the host wired for the lowest latency.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: deskbridge` | Run `pip install -e .` from the `remote/` folder first. |
| "Unreachable" on Connect | Host is off / wrong IP / VNC server not started. Re-check step 3. |
| Viewer doesn't open on Windows | Install the TigerVNC **viewer**; ensure `vncviewer.exe` is on PATH. |
| Laggy / freeze-then-jump from a Mac | Install TigerVNC viewer (`brew install --cask tigervnc`) so DeskBridge stops using Apple's throttled client; try the **Fast** quality preset. |
| Mouse cursor offset / clicks land wrong | Use TigerVNC viewer (any quality preset sets `RemoteResize` for 1:1 mapping). |
| Want true 60 fps / gaming | VNC can't do it — use Moonlight + Sunshine (see the Gaming section). |
| Can connect but black screen / no control | Re-check the host's VNC password and that "allow control" is enabled. |

## Run the tests

```
cd remote
python -m pytest -q
```
