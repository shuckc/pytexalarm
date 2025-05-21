#!/usr/bin/env python
from __future__ import annotations

import argparse
import asyncio
from functools import partial
from itertools import count
from typing import Any

from . import DEFAULT_MEMFILE
from .pialarm import (
    PanelDecoder,
    get_bcd,
    get_panel_decoder,
    interactive_shell,
    panel_from_file,
)
from .udl import SerialWintex
from .webapp import start_server

PORT = 10001
WEBPORT = 10002

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    "--banner",
    help="Specify the panel to identify as\nUse 'Premier 832 V4.0' for an 832",
    default="Elite 24    V4.02.01",
)
parser.add_argument(
    "--verbose", help="Print instructions", action="store_true", default=False
)
parser.add_argument(
    "--debug", help="Print bytes on wire", action="store_true", default=False
)
parser.add_argument(
    "--mem", help="read/write panel config from MEMFILE", default=DEFAULT_MEMFILE
)
parser.add_argument("--udl-port", help="UDL port", default=PORT, type=int)
parser.add_argument("--udl-password", help="UDL password", default="1234")
parser.add_argument("--web-port", help="web port", default=WEBPORT, type=int)

# How much memory to spend (at most) on each call to recv. Pretty arbitrary,
# but shouldn't be too big or too small.
BUFSIZE = 16384
CONNECTION_COUNTER = count()

ACK_MSG = b"\06"

KEY_MAP = {
    0x01: "Digit 1",
    0x02: "Digit 2",
    0x03: "Digit 3",
    0x04: "Digit 4",
    0x05: "Digit 5",
    0x06: "Digit 6",
    0x07: "Digit 7",
    0x08: "Digit 8",
    0x09: "Digit 9",
    0x0A: "Digit 0",
    0x0B: "Omit",
    0x0C: "Menu",
    0x0D: "Yes",
    0x0E: "Part",
    0x0F: "No",
    0x10: "Area",
    0x14: "Chime",
    0x15: "Reset",
    0x16: "Up",
    0x17: "Down",
}


def unpack_mem_proto(region: bytes, msg_body: bytes) -> tuple[int, int, bytes, bytes]:
    base = (msg_body[0] << 16) + (msg_body[1] << 8) + msg_body[2]
    sz = msg_body[3]
    if len(msg_body) not in [4, sz + 4]:
        raise Exception(
            f"config read/write len {sz} vs. data payload {len(msg_body)} mismatch"
        )
    old_data = region[base : base + sz]
    wr_data = msg_body[4:]
    return (base, sz, wr_data, old_data)


def hexbytes(data: bytes) -> str:
    return ",".join(hex(x) for x in data)


class SerialWintexPanel(SerialWintex):
    def __init__(self, panel: PanelDecoder, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.serial: bytes = b"\x01\x00\x07\x09\x04\x07\x01"
        self.panel: PanelDecoder = panel
        self.outbound: list[bytes] = []

    def handle_msg(self, body: bytes) -> bytes | None:
        mtype = body[0:1].decode()
        body = body[1:]

        # commands we will store and destination region
        if mtype == "Z" and len(body) == 0:
            print(f"Sending login prompt for serial '{get_bcd(self.serial, 0, 7)}'")
            # unsure of the significance of this 0x05
            return b"Z\x05" + self.serial
        elif mtype == "Z":
            login = body.decode()
            print(f"Recieved UDL login '{login}'.")
            self.check_udl_login(login)
            print(f"Sending panel identification '{self.panel.banner}'")
            assert len(self.panel.banner) == 20
            return ("Z" + self.panel.banner).encode()
        elif mtype == "H":
            print("Wintex hang up")
            return b"\03\06\xf6"
        # wintex shows 'Reading UDL options'
        elif mtype == "O":  # configuration read
            base, sz, wr_data, old_data = unpack_mem_proto(self.panel.mem, body)
            print(
                f"Configuration read addr={base:06x} sz={sz:01x} data={old_data.hex()}"
            )
            return b"I" + body[0:4] + old_data  # echo back addr and sz
        elif mtype == "I":  # configuration write
            base, sz, wr_data, old_data = unpack_mem_proto(self.panel.mem, body)
            print(
                f"Configuration write addr={base:06x} sz={sz:01x} data={wr_data.hex()}"
            )
            self.print_deltas(base, old_data, wr_data)
            self.panel.mem[base : base + sz] = wr_data
            return ACK_MSG
        elif mtype == "R":  # live state read
            base, sz, wr_data, old_data = unpack_mem_proto(self.panel.io, body)
            print(
                f"Live state read addr={base:06x} sz={sz:01x} data={hexbytes(old_data)}"
            )
            return b"W" + body[0:4] + old_data
        elif mtype == "W":  # live state write
            base, sz, wr_data, old_data = unpack_mem_proto(self.panel.io, body)
            print(f"Live state write addr={base:06x} sz={sz:01x}")
            self.print_deltas(base, old_data, wr_data)
            self.panel.io[base : base + sz] = wr_data
            return ACK_MSG
        elif mtype == "P":  # Heartbeat
            return b"P\xff\xff"
        elif mtype == "K":  # Keypad press
            print(f"Keypad {body[0]} pressed 0x{body[1]:02x} - {KEY_MAP.get(body[1])}")
            return ACK_MSG
        elif mtype == "U":  # Special action?
            # U 01 - commit zone, expander changes
            if body[0] == 1:
                print("Committing zone changes?")
                return ACK_MSG
            elif body[0] == 64:
                print("Sending message to keypads")
                return ACK_MSG
            else:
                print(f"Unknown U special action {mtype} with args {body!r}")
        elif mtype == "A":
            print(f"Arming area {body[0]}")
            return ACK_MSG
        elif mtype == "C":
            print(f"Resetting area {body[0]}")
            return ACK_MSG
        elif mtype == "S":
            print(f"Part arming area {body[0]} type={body[1]}")
            return ACK_MSG
        elif mtype == "B":
            # RTC programming done via. B with args [56, 9, 29, 1, 0]
            if body == b"\56\00\29\01\00":
                print("RTC initialise special op 1")
                return ACK_MSG
            elif body == b"\57\09\29\01\00":
                print("RTC initialise special op 2")
                return ACK_MSG
            else:
                print(f"Unknown B special RTC action {mtype} with args {body!r}")
                return ACK_MSG
        else:
            print(f"Unknown command {mtype} with args {body!r}")
        return None

    def send_bytes(self, message: bytes) -> None:
        self.outbound.append(message)

    def print_deltas(self, base: int, old: bytes, new: bytes) -> None:
        if old != new:
            for n, (i, j) in enumerate(zip(old, new)):
                if i != j:
                    print(f"  mem: updated {base + n:06x} old={i:02x} new={j:02x}")

    def check_udl_login(self, login: str) -> None:
        pass


async def udl_server(
    panel: PanelDecoder,
    debug: bool,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    # Assign each connection a unique number to make our debug prints easier
    # to understand when there are multiple simultaneous connections.
    ser = SerialWintexPanel(panel, direction="tcp")
    ident = next(CONNECTION_COUNTER)
    print(f"udl_server {ident}: connected")
    try:
        while True:
            data = await reader.read(BUFSIZE)
            if debug:
                print(f"udl_server {ident}: received data {data!r}")

            if not data:
                print(f"udl_server {ident}: connection closed")
                return

            ser.on_bytes(data)
            for out in ser.outbound:
                if debug:
                    print(f" udl_server {ident}: sending {out!r}")
                writer.write(out)
            del ser.outbound[:]

    except Exception as exc:
        # Unhandled exceptions will propagate into our parent and take
        # down the whole program. If the exception is KeyboardInterrupt,
        # that's what we want, but otherwise maybe not...
        print(f"udl_server {ident}: crashed: {exc!r}")
        raise


async def main() -> None:
    args = parser.parse_args()

    panel: PanelDecoder
    if args.mem:
        print(f"Reading from {args.mem}")
        panel = panel_from_file(args.mem)
    elif args.banner:
        print("Defaulting from banner")
        panel = get_panel_decoder(args.banner)
    else:
        raise ValueError("Supply panel banner or file!")

    print(
        f"Panel type '{panel}' with UDL password {args.udl_password} backed by file {args.mem}"
    )

    server = await asyncio.start_server(
        partial(udl_server, panel, args.debug), None, args.udl_port
    )
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Serving UDL on {addrs}")

    if args.web_port > 0:
        await start_server(panel, args.web_port)

    try:
        await interactive_shell(panel, server=server)
    except Exception as e:
        print(e)


asyncio.run(main())
