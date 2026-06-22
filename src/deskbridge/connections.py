"""Connection model and JSON persistence for saved machines."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Connection:
    name: str
    host: str
    port: int = 5900
    tailscale_name: str | None = None
    notes: str = ""
    quality: str = "balanced"


def default_config_path() -> Path:
    """Location of the saved-connections file under the user's home."""
    return Path.home() / ".deskbridge" / "connections.json"


def load_connections(path: Path) -> list[Connection]:
    """Load connections from JSON; return [] if the file does not exist."""
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [Connection(**item) for item in data]


def save_connections(path: Path, connections: list[Connection]) -> None:
    """Write connections to JSON, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(c) for c in connections], indent=2))
