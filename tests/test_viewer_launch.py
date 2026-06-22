# tests/test_viewer_launch.py
import pytest

from deskbridge.viewer_launch import build_viewer_command


def test_macos_command():
    cmd = build_viewer_command("macos", "192.168.1.5", 5900)
    assert cmd == ["open", "vnc://192.168.1.5:5900"]


def test_windows_command_default_path():
    cmd = build_viewer_command("windows", "192.168.1.5", 5901)
    assert cmd == ["vncviewer.exe", "192.168.1.5::5901"]


def test_windows_command_custom_path():
    cmd = build_viewer_command(
        "windows", "host", 5900, tigervnc_path=r"C:\Tools\vncviewer.exe"
    )
    assert cmd == [r"C:\Tools\vncviewer.exe", "host::5900"]


def test_unsupported_os_raises():
    with pytest.raises(ValueError):
        build_viewer_command("other", "host", 5900)
