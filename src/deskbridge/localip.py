"""Determine this machine's primary LAN IPv4 address."""

import socket


def local_ip() -> str | None:
    """Return this machine's primary LAN IPv4 address, or None if unavailable.

    Uses a UDP socket "connected" to a public address: no packets are sent, but
    the OS assigns the local interface it would route through, which
    getsockname() reports as the real LAN IP. More reliable cross-platform than
    gethostbyname(gethostname()), which often returns 127.0.0.1 on macOS.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None
