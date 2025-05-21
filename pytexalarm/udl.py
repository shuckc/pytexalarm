from typing import Optional, Protocol, Tuple

from .hexdump import printable


# speak the UDL low-level protocol. Recieve frames in 'on_byes', buffer until the next header's length
# is available, validate CRC and then pass to parse_msg. If a reply is produced, add length prefix and CRC
# then pass this to subclass 'send_bytes'.
def udl_checksum(data: bytes) -> int:
    sz = data[0]
    if sz != len(data):
        raise ValueError("length does not match framing!")
    # subtract each byte from 0xff
    v = 255
    for b in data:
        v -= b
    return v % 256


def udl_frame(msg: bytes) -> bytes:
    msglen = len(msg)
    if msglen > 253:
        raise ValueError("Cannot frame overlong message")
    data = bytearray(msglen + 2)
    data[0] = msglen + 2
    data[1 : msglen + 1] = msg
    data[msglen + 1] = udl_checksum(data)
    # assert udl_verify(data) == 0
    return data


def udl_verify(data: bytes) -> bool:
    return udl_checksum(data) == 0


class UDLClient(Protocol):
    async def read_mem(self, base: int, sz: int) -> bytes: ...
    async def read_identification(self) -> str: ...


class SerialWintex:
    def __init__(self, direction: str = "", verbose: bool = False, debug: bool = False):
        self.buf = bytearray()
        self.verbose = verbose
        self.debug = debug
        self.direction = direction

    def on_bytes(self, bytes_message: bytes) -> None:
        self.buf.extend(bytes_message)
        if self.debug:
            print(f" buffer: {self.direction:4s} {self.buf}")
        # have we a full message in this direction
        while len(self.buf) > 0 and len(self.buf) >= self.buf[0]:
            sz = self.buf[0]
            msg = self.buf[0:sz]
            if udl_verify(msg):
                self.log_msg(msg)
                # handle_msg does not need (or return) length and checksum
                reply = self.handle_msg(msg[1 : sz - 1])
                if reply:
                    omsg = udl_frame(reply)
                    self.log_msg(reply)
                    self.send_bytes(omsg)
                del self.buf[0:sz]
            else:
                print(f"Warning: bad UDL checksum for {self.direction} at {self.buf}")
                # recover from 'ATZ\r' if found
                try:
                    rpos = self.buf.index(b"ATZ\r")
                    print(f"removing before index {rpos}")
                    del self.buf[: rpos + 4]
                except ValueError:
                    print("emptying buffer")
                    del self.buf[:]

    def log_msg(self, msg: bytes) -> None:
        mtype = msg[0]
        printable_type = printable(mtype)
        msg_hex = " ".join("{:02x}".format(m) for m in msg[1:])
        msg_ascii = "".join(printable(c) for c in msg[1:])
        if self.verbose:
            print(f"  {self.direction:4s} {printable_type} {msg_hex} | {msg_ascii} ")

    def handle_msg(self, body: bytes) -> Optional[bytes]:
        # subclass for handling logic
        raise ValueError()

    def send_bytes(self, msg: bytes) -> None:
        # optional subclass if sending replies
        pass


# UDL memory/io read and writes over 64 bytes are split into 64-byte ranges.
# to reduce the boilerplate storing the smaller ranges, we can compact/uncompact
# them into equivelent larger ranges.
#  invarient:  uncompact_ranges(compact_ranges(ranges)) == ranges
#
def compact_ranges(mem_ranges: list[Tuple[int, int]]) -> list[Tuple[int, int]]:
    # post-process contiguous reads of 64-bytes into a single read
    compacted = []
    last: Optional[tuple[int, int]] = None
    for base, sz in mem_ranges:
        if last:
            if base == last[0] + last[1]:  # read starts from last
                last = (last[0], last[1] + sz)
                continue
            compacted.append(last)
            last = None
        if sz < 64:
            compacted.append((base, sz))
        else:
            last = (base, sz)
    if last:
        compacted.append(last)
    return compacted


def uncompact_ranges(mem_ranges: list[Tuple[int, int]]) -> list[Tuple[int, int]]:
    uncompacted = []
    for base, sz in mem_ranges:
        while sz > 64:
            uncompacted.append((base, 64))
            sz = sz - 64
            base = base + 64
        uncompacted.append((base, sz))
    return uncompacted
