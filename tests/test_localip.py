from unittest import mock

from deskbridge.localip import local_ip


def test_local_ip_returns_getsockname_address():
    fake_sock = mock.MagicMock()
    fake_sock.getsockname.return_value = ("192.168.1.42", 54321)
    fake_sock.__enter__.return_value = fake_sock
    with mock.patch("socket.socket", return_value=fake_sock):
        assert local_ip() == "192.168.1.42"
    fake_sock.connect.assert_called_once_with(("8.8.8.8", 80))


def test_local_ip_returns_none_on_oserror():
    with mock.patch("socket.socket", side_effect=OSError):
        assert local_ip() is None
