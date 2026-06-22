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
from deskbridge.viewer_launch import launch_viewer
from deskbridge.vnc_server import is_server_running, setup_instructions


class DeskBridgeApp:
    def __init__(self, root: tk.Tk, config_path: Path):
        self.root = root
        self.config_path = config_path
        self.os_name = current_os()
        self.local_ip = local_ip() or "unavailable"
        self.connections = load_connections(config_path)

        root.title("DeskBridge")
        root.geometry("420x360")

        tk.Label(
            root, text=f"This machine: {self.os_name} · IP: {self.local_ip}"
        ).pack(anchor="w", padx=8, pady=4)

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

        self.status = tk.Label(root, text="", anchor="w", fg="gray")
        self.status.pack(fill="x", padx=8, pady=4)

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for c in self.connections:
            self.listbox.insert(tk.END, f"{c.name} — {c.host}:{c.port}")

    def _selected(self) -> Connection | None:
        sel = self.listbox.curselection()
        return self.connections[sel[0]] if sel else None

    def _on_select(self, event=None):
        conn = self._selected()
        if conn:
            self.quality_var.set(conn.quality.capitalize())

    def _on_quality_change(self, value):
        conn = self._selected()
        if conn:
            conn.quality = value.lower()
            save_connections(self.config_path, self.connections)

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
        launch_viewer(self.os_name, address, conn.port, quality=conn.quality)
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
        address_line = f"Other machines connect to this machine at: {self.local_ip}\n\n"
        prefix = "VNC server appears to be running.\n\n" if running else ""
        messagebox.showinfo("Share my screen", address_line + prefix + steps)
