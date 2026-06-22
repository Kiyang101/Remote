# tests/test_net.py
from unittest import mock

from deskbridge.connections import Connection
from deskbridge.net import resolve_address, is_port_open


def test_resolve_prefers_lan_host_by_default():
    c = Connection(name="x", host="192.168.1.5", tailscale_name="x-ts")
    assert resolve_address(c, use_tailscale=False) == "192.168.1.5"


def test_resolve_uses_tailscale_when_requested():
    c = Connection(name="x", host="192.168.1.5", tailscale_name="x-ts")
    assert resolve_address(c, use_tailscale=True) == "x-ts"


def test_resolve_falls_back_to_host_when_no_tailscale_name():
    c = Connection(name="x", host="192.168.1.5", tailscale_name=None)
    assert resolve_address(c, use_tailscale=True) == "192.168.1.5"


def test_is_port_open_true_when_connect_succeeds():
    fake_sock = mock.MagicMock()
    with mock.patch("socket.create_connection", return_value=fake_sock) as cc:
        assert is_port_open("host", 5900, timeout=0.1) is True
        cc.assert_called_once()


def test_is_port_open_false_on_oserror():
    with mock.patch("socket.create_connection", side_effect=OSError):
        assert is_port_open("host", 5900, timeout=0.1) is False
