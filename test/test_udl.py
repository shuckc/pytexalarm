import pytest


from pytexalarm.pialarm import udl_verify, udl_frame


def test_checksum() -> None:
    assert udl_verify(bytes.fromhex("03 5a a2")) is True
    assert udl_verify(bytes.fromhex("03 5a a3")) is False

    assert (
        udl_verify(
            bytes.fromhex(
                "17 5a 45 6c 69 74 65 20 32 34 20 20 20 20 56 36 2e 30 35 2e 30 33 e5"
            )
        )
        is True
    )
    with pytest.raises(ValueError):
        udl_verify(
            bytes.fromhex(
                "16 5a 45 6c 69 74 65 20 32 34 20 20 20 20 56 36 2e 30 35 2e 30 33 e5"
            )
        )

    assert udl_verify(bytes.fromhex("08 49 00 16 78 01 06 19")) is True


def test_frame() -> None:
    assert udl_frame(b"Z") == b"\x03Z\xa2"
    assert udl_frame(b"P") == b"\x03P\xac"
    assert udl_frame(b"ZElite 24    V6.05.03") == b"\x17ZElite 24    V6.05.03\xe5"
