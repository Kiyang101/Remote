# tests/test_vnc_server.py
from unittest import mock

import pytest

from deskbridge.vnc_server import setup_instructions, is_server_running


def test_macos_instructions_mention_screen_sharing():
    text = setup_instructions("macos")
    assert "Screen Sharing" in text


def test_windows_instructions_mention_tigervnc():
    text = setup_instructions("windows")
    assert "TigerVNC" in text


def test_unsupported_os_raises():
    with pytest.raises(ValueError):
        setup_instructions("other")


def test_is_server_running_checks_local_port():
    with mock.patch("deskbridge.vnc_server.is_port_open", return_value=True) as p:
        assert is_server_running(5900) is True
        p.assert_called_once_with("127.0.0.1", 5900, timeout=0.5)
