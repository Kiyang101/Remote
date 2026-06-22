"""Read the local tailnet via the Tailscale CLI."""

import json
import os
import shutil
import subprocess
from dataclasses import dataclass

MACOS_APP_CLI = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"


@dataclass
class TailnetMachine:
    name: str
    address: str
    online: bool


def tailscale_cli_path() -> str | None:
    """Locate the Tailscale CLI: macOS app binary, then PATH, else None."""
    if os.path.exists(MACOS_APP_CLI):
        return MACOS_APP_CLI
    return shutil.which("tailscale")


def is_installed() -> bool:
    return tailscale_cli_path() is not None


def _machine_from_node(node: dict) -> TailnetMachine | None:
    ips = node.get("TailscaleIPs") or []
    if not ips:
        return None
    name = node.get("HostName") or (node.get("DNSName") or "").split(".")[0]
    return TailnetMachine(
        name=name or "unknown",
        address=ips[0],
        online=bool(node.get("Online", False)),
    )


def parse_status(data: dict) -> tuple[TailnetMachine | None, list[TailnetMachine]]:
    """From `tailscale status --json`, return (self_machine, peers).

    Nodes without a Tailscale IP are skipped.
    """
    self_node = data.get("Self")
    self_machine = _machine_from_node(self_node) if self_node else None
    peers = []
    for node in (data.get("Peer") or {}).values():
        machine = _machine_from_node(node)
        if machine:
            peers.append(machine)
    return self_machine, peers


def _run_status_json(cli_path: str) -> dict | None:
    try:
        result = subprocess.run(
            [cli_path, "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except ValueError:
        return None


def _status() -> dict | None:
    cli = tailscale_cli_path()
    if cli is None:
        return None
    return _run_status_json(cli)


def self_machine() -> TailnetMachine | None:
    data = _status()
    return parse_status(data)[0] if data is not None else None


def peers() -> list[TailnetMachine]:
    data = _status()
    return parse_status(data)[1] if data is not None else []
