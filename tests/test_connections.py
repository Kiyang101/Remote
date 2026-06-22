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


def test_quality_defaults_to_balanced():
    c = Connection(name="x", host="h")
    assert c.quality == "balanced"


def test_quality_roundtrips_and_tolerates_legacy_json(tmp_path):
    path = tmp_path / "connections.json"
    save_connections(path, [Connection(name="A", host="h", quality="fast")])
    assert load_connections(path)[0].quality == "fast"

    # Legacy entry written before the quality field existed must still load.
    path.write_text('[{"name": "B", "host": "h2", "port": 5900, '
                    '"tailscale_name": null, "notes": ""}]')
    loaded = load_connections(path)
    assert loaded[0].name == "B"
    assert loaded[0].quality == "balanced"
