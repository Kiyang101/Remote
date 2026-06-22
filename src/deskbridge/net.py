"""Resolve a connection to a reachable address and test VNC reachability."""

import socket

from deskbridge.connections import Connection


def resolve_address(conn: Connection, use_tailscale: bool) -> str:
    """Pick the address to connect to: Tailscale name if requested+available,
    otherwise the LAN host."""
    if use_tailscale and conn.tailscale_name:
        return conn.tailscale_name
    return conn.host


def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
