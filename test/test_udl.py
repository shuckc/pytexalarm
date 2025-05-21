import random

import pytest

from pytexalarm.udl import compact_ranges, udl_frame, udl_verify, uncompact_ranges


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


@pytest.fixture
def notrandom() -> None:
    random.seed(0)


def test_compact_uncompact_ranges(notrandom: None) -> None:
    assert compact_ranges([(1, 1)]) == [(1, 1)]
    assert compact_ranges([(1, 1), (2, 2)]) == [(1, 1), (2, 2)]
    assert compact_ranges([(0, 64), (64, 16)]) == [(0, 80)]
    assert uncompact_ranges([(0, 80)]) == [(0, 64), (64, 16)]

    for i in range(100):
        c = random.randrange(10)
        gs = []
        for _ in range(c):
            sz = random.randrange(0xFFFF)
            base = random.randrange(0xFFFFFF)
            gs.append((base, sz))
        print(gs)
        assert compact_ranges(uncompact_ranges(gs)) == gs
