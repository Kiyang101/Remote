# src/deskbridge/app.py
"""DeskBridge entry point: launch the connection-manager window."""

import tkinter as tk

from deskbridge.connections import default_config_path
from deskbridge.gui import DeskBridgeApp


def main() -> None:
    root = tk.Tk()
    DeskBridgeApp(root, default_config_path())
    root.mainloop()


if __name__ == "__main__":
    main()
