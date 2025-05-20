# https://gist.github.com/NeatMonster/c06c61ba4114a2b31418a364341c26c0
from typing import Iterator


def printable(c: int) -> str:  # c should be int 0..255
    return chr(c) if 32 <= c < 127 else "."


class hexdump:
    def __init__(self, buf: bytes, off: int = 0, ind: int = 0):
        self.buf = buf
        self.off = off
        self.indent = " " * ind

    def __iter__(self) -> Iterator[str]:
        last_bs, last_line = None, None
        for i in range(0, len(self.buf), 16):
            bs = bytearray(self.buf[i : i + 16])
            line = "{}{:08x}  {:23}  {:23}  |{:16}|".format(
                self.indent,
                self.off + i,
                " ".join(("{:02x}".format(x) for x in bs[:8])),
                " ".join(("{:02x}".format(x) for x in bs[8:])),
                "".join((chr(x) if 32 <= x < 127 else "." for x in bs)),
            )
            if bs == last_bs:
                line = "*"
            if bs != last_bs or line != last_line:
                yield line
            last_bs, last_line = bs, line
        yield "{}{:08x}".format(self.indent, self.off + len(self.buf))

    def __str__(self) -> str:
        return "\n".join(self)

    def __repr__(self) -> str:
        return "\n".join(self)
