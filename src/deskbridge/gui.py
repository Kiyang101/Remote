"""Tkinter connection-manager window for DeskBridge."""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

from deskbridge.connections import (
    Connection,
    load_connections,
    save_connections,
)
from deskbridge.localip import local_ip
from deskbridge.net import is_port_open, resolve_address
from deskbridge.platform_detect import current_os
from deskbridge.tailscale import (
    is_installed as tailscale_is_installed,
    peers as tailscale_peers,
    self_machine as tailscale_self_machine,
)
from deskbridge.viewer_launch import launch_viewer
from deskbridge.vnc_server import is_server_running, setup_instructions

_INSTALL_TAILSCALE_MSG = (
    "Tailscale is not installed.\n\n"
    "Install it and log in with the same account on both machines:\n"
    "  • macOS:   brew install --cask tailscale\n"
    "  • Windows: https://tailscale.com/download\n\n"
    "Then flip 'Use Tailscale' on again."
)


class DeskBridgeApp:
    def __init__(self, root: tk.Tk, config_path: Path):
        self.root = root
        self.config_path = config_path
        self.os_name = current_os()
        self.local_ip = local_ip() or "unavailable"
        self.connections = load_connections(config_path)
        # Defined before the first _refresh_list so it can branch on the mode.
        self.use_tailscale = tk.BooleanVar(value=False)
        self._tailnet: list = []

        root.title("DeskBridge")
        root.geometry("420x380")

        tk.Label(
            root, text=f"This machine: {self.os_name} · IP: {self.local_ip}"
        ).pack(anchor="w", padx=8, pady=(4, 0))

        sm = tailscale_self_machine()
        ts_text = (
            f"Tailscale: {sm.name} ({sm.address})" if sm else "Tailscale: not installed"
        )
        tk.Label(root, text=ts_text, fg="gray").pack(anchor="w", padx=8, pady=(0, 4))

        self.listbox = tk.Listbox(root)
        self.listbox.pack(fill="both", expand=True, padx=8, pady=4)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self._refresh_list()

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

        tk.Checkbutton(
            root, text="Use Tailscale (internet)", variable=self.use_tailscale,
            command=self._toggle_tailscale,
        ).pack(anchor="w", padx=8)

        self.status = tk.Label(root, text="", anchor="w", fg="gray")
        self.status.pack(fill="x", padx=8, pady=4)

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        if self.use_tailscale.get():
            self._tailnet = tailscale_peers()
            for m in self._tailnet:
                mark = "online" if m.online else "offline"
                self.listbox.insert(tk.END, f"{m.name} — {m.address} ({mark})")
        else:
            for c in self.connections:
                self.listbox.insert(tk.END, f"{c.name} — {c.host}:{c.port}")

    def _selected_index(self) -> int | None:
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def _toggle_tailscale(self):
        if self.use_tailscale.get() and not tailscale_is_installed():
            messagebox.showinfo("Tailscale not installed", _INSTALL_TAILSCALE_MSG)
            self.use_tailscale.set(False)
            return
        self._refresh_list()
        if self.use_tailscale.get():
            if self._tailnet:
                self.status.config(text="Tailscale mode: showing tailnet machines.")
            else:
                self.status.config(
                    text="Tailscale on, but no peers (is it running and logged in?)."
                )
        else:
            self.status.config(text="LAN mode.")

    def _on_select(self, event=None):
        if self.use_tailscale.get():
            return
        i = self._selected_index()
        if i is not None:
            self.quality_var.set(self.connections[i].quality.capitalize())

    def _on_quality_change(self, value):
        if self.use_tailscale.get():
            return
        i = self._selected_index()
        if i is not None:
            self.connections[i].quality = value.lower()
            save_connections(self.config_path, self.connections)

    def connect(self):
        i = self._selected_index()
        if i is None:
            self.status.config(text="Select a machine first.")
            return
        if self.use_tailscale.get():
            machine = self._tailnet[i]
            address, port = machine.address, 5900
            quality, label = self.quality_var.get().lower(), machine.name
        else:
            conn = self.connections[i]
            address = resolve_address(conn, use_tailscale=False)
            port, quality, label = conn.port, conn.quality, conn.name
        self.status.config(text=f"Checking {address}:{port}…")
        self.root.update_idletasks()
        if not is_port_open(address, port, timeout=2.0):
            messagebox.showwarning(
                "Unreachable",
                f"Could not reach {address}:{port}.\n\n"
                "Check the machine is on and its VNC server is running.",
            )
            self.status.config(text="Unreachable.")
            return
        launch_viewer(self.os_name, address, port, quality=quality)
        self.status.config(text=f"Launched viewer for {label}.")

    def add_machine(self):
        if self.use_tailscale.get():
            self.status.config(text="Switch off Tailscale to edit saved machines.")
            return
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
        if self.use_tailscale.get():
            self.status.config(text="Switch off Tailscale to edit saved machines.")
            return
        i = self._selected_index()
        if i is None:
            return
        del self.connections[i]
        save_connections(self.config_path, self.connections)
        self._refresh_list()

    def share_screen(self):
        running = is_server_running()
        steps = setup_instructions(self.os_name)
        address_line = f"Other machines connect to this machine at: {self.local_ip}\n\n"
        prefix = "VNC server appears to be running.\n\n" if running else ""
        messagebox.showinfo("Share my screen", address_line + prefix + steps)
