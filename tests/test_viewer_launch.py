from unittest import mock

import pytest

from deskbridge.viewer_launch import (
    build_viewer_command,
    macos_tigervnc_path,
    quality_flags,
)

VNCVIEWER = "/Applications/TigerVNC.app/Contents/MacOS/vncviewer"


def test_quality_flags_balanced():
    assert quality_flags("balanced") == [
        "-RemoteResize=1",
        "-AlwaysCursor=1",
        "-PreferredEncoding=Tight",
        "-QualityLevel=7",
        "-CompressLevel=2",
        "-FullColor=1",
    ]


def test_quality_flags_fast():
    assert quality_flags("fast") == [
        "-RemoteResize=1",
        "-AlwaysCursor=1",
        "-PreferredEncoding=Tight",
        "-QualityLevel=4",
        "-CompressLevel=6",
        "-FullColor=0",
        "-LowColorLevel=1",
    ]


def test_quality_flags_sharp():
    assert quality_flags("sharp") == [
        "-RemoteResize=1",
        "-AlwaysCursor=1",
        "-PreferredEncoding=Tight",
        "-QualityLevel=9",
        "-CompressLevel=1",
        "-FullColor=1",
    ]


def test_quality_flags_unknown_raises():
    with pytest.raises(ValueError):
        quality_flags("ultra")


def test_macos_command_uses_tigervnc_when_available():
    cmd = build_viewer_command(
        "macos", "192.168.1.5", 5900, quality="balanced", tigervnc_path=VNCVIEWER
    )
    assert cmd == [VNCVIEWER, "192.168.1.5::5900", *quality_flags("balanced")]


def test_macos_command_falls_back_to_open_without_tigervnc():
    cmd = build_viewer_command("macos", "192.168.1.5", 5900, tigervnc_path=None)
    assert cmd == ["open", "vnc://192.168.1.5:5900"]


def test_windows_command_default_path_includes_flags():
    cmd = build_viewer_command("windows", "192.168.1.5", 5901, quality="fast")
    assert cmd == ["vncviewer.exe", "192.168.1.5::5901", *quality_flags("fast")]


def test_windows_command_custom_path():
    cmd = build_viewer_command(
        "windows", "host", 5900, tigervnc_path=r"C:\Tools\vncviewer.exe"
    )
    assert cmd == [r"C:\Tools\vncviewer.exe", "host::5900", *quality_flags("balanced")]


def test_unsupported_os_raises():
    with pytest.raises(ValueError):
        build_viewer_command("other", "host", 5900)


def test_macos_tigervnc_path_found():
    with mock.patch("os.path.exists", return_value=True):
        assert macos_tigervnc_path() == VNCVIEWER


def test_macos_tigervnc_path_missing():
    with mock.patch("os.path.exists", return_value=False):
        assert macos_tigervnc_path() is None
