# tests/test_connections.py
from deskbridge.connections import Connection, load_connections, save_connections


def test_roundtrip(tmp_path):
    path = tmp_path / "connections.json"
    conns = [
        Connection(name="My Windows", host="192.168.1.42", port=5900, notes="desk PC"),
        Connection(name="My Mac", host="mac.local", port=5900),
    ]
    save_connections(path, conns)
    loaded = load_connections(path)
    assert loaded == conns


def test_load_missing_file_returns_empty(tmp_path):
    assert load_connections(tmp_path / "nope.json") == []


def test_defaults():
    c = Connection(name="x", host="h")
    assert c.port == 5900
    assert c.tailscale_name is None
    assert c.notes == ""
