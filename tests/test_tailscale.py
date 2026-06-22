from unittest import mock

from deskbridge import tailscale as ts
from deskbridge.tailscale import TailnetMachine, parse_status

SAMPLE = {
    "Self": {
        "HostName": "my-mac",
        "DNSName": "my-mac.tailnet.ts.net.",
        "TailscaleIPs": ["100.64.0.1"],
        "Online": True,
    },
    "Peer": {
        "nodekey:abc": {
            "HostName": "my-windows",
            "DNSName": "my-windows.tailnet.ts.net.",
            "TailscaleIPs": ["100.64.0.2"],
            "Online": True,
        },
        "nodekey:def": {
            "HostName": "old-laptop",
            "DNSName": "old-laptop.tailnet.ts.net.",
            "TailscaleIPs": [],
            "Online": False,
        },
    },
}


def test_parse_status_self_and_peers():
    self_m, peers = parse_status(SAMPLE)
    assert self_m == TailnetMachine("my-mac", "100.64.0.1", True)
    # old-laptop has no IP and is skipped
    assert peers == [TailnetMachine("my-windows", "100.64.0.2", True)]


def test_parse_status_empty():
    self_m, peers = parse_status({})
    assert self_m is None
    assert peers == []


def test_cli_path_prefers_macos_app():
    with mock.patch("os.path.exists", return_value=True):
        assert ts.tailscale_cli_path() == ts.MACOS_APP_CLI


def test_cli_path_falls_back_to_which():
    with mock.patch("os.path.exists", return_value=False), \
         mock.patch("shutil.which", return_value="/usr/bin/tailscale"):
        assert ts.tailscale_cli_path() == "/usr/bin/tailscale"


def test_cli_path_none_when_absent():
    with mock.patch("os.path.exists", return_value=False), \
         mock.patch("shutil.which", return_value=None):
        assert ts.tailscale_cli_path() is None
        assert ts.is_installed() is False


def test_run_status_json_ok():
    completed = mock.Mock(returncode=0, stdout='{"Self": {}}')
    with mock.patch("subprocess.run", return_value=completed):
        assert ts._run_status_json("tailscale") == {"Self": {}}


def test_run_status_json_nonzero_returns_none():
    completed = mock.Mock(returncode=1, stdout="")
    with mock.patch("subprocess.run", return_value=completed):
        assert ts._run_status_json("tailscale") is None


def test_run_status_json_bad_json_returns_none():
    completed = mock.Mock(returncode=0, stdout="not json")
    with mock.patch("subprocess.run", return_value=completed):
        assert ts._run_status_json("tailscale") is None


def test_run_status_json_oserror_returns_none():
    with mock.patch("subprocess.run", side_effect=OSError):
        assert ts._run_status_json("tailscale") is None
