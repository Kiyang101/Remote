from deskbridge.platform_detect import normalize_os


def test_normalize_macos():
    assert normalize_os("Darwin") == "macos"


def test_normalize_windows():
    assert normalize_os("Windows") == "windows"


def test_normalize_other():
    assert normalize_os("Linux") == "other"
