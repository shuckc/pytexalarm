from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Iterable, Tuple

from . import DEFAULT_MEMFILE
from .pialarm import (
    PanelDecoder,
    get_bcd,
    get_panel_decoder,
)
from .udl import SerialWintex

# reads a ser2net trace files from stdin and prints the high-level operations.
# Optionally writes the implied contents of panel memory to MEMFILE
# verifies serial checksums in the trace in both directions
# e.g. $ cat traces/wintex-ser2net/*.trace | python -m pytexalarm.trace2op --mem blob.mem --json


# This class expects to be called on UDL responses stream, not UDL queries!
class SerialWintexPanel(SerialWintex):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.serial: str | None = None
        self.panel: PanelDecoder | None = None
        self.mem_ranges: list[Tuple[int, int]] = []

    def handle_msg(self, body: bytes) -> None:
        # commands we will store and destination region
        mtype: str = body[0:1].decode()  # first char should be printable

        if mtype == "Z" and self.serial is None:
            # bytes are 8 characters of BCD serial number
            self.serial = get_bcd(body, 1, len(body) - 1)
            print(f"detected serial {self.serial}")
        elif mtype == "Z" and self.panel is None:
            banner = body[1:].decode()
            print(f"detected panel banner '{banner}'")
            self.panel = get_panel_decoder(banner)
            if self.serial:
                self.panel.serial = self.serial  # we learnt this prior
        elif self.panel:
            parts = {("term", "I"): self.panel.mem, ("term", "W"): self.panel.io}
            c = parts.get((self.direction, mtype), None)
            if c:
                base = (body[1] << 16) + (body[2] << 8) + body[3]
                sz = body[4]
                payload = body[5:]
                if sz + 5 != len(body):
                    raise Exception("IO length byte does not match msg payload sz")
                c[base : base + sz] = payload
                if mtype == "I":
                    self.mem_ranges.append((base, sz))
                # print(f"storing msg {mtype} payload={payload!r} to {base:02x}")
            elif mtype == "P":  # heartbeat
                pass
            elif body[0] == 6:  # hangup non-printable
                pass
            else:
                print(f"ignoring msg {self.direction}/{mtype} {body!r}")
            return None
        else:
            print(f"panel not identified at {self.direction}/{mtype} {body!r}")


class SerialWintexIgnore(SerialWintex):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.udlpasswd: str | None = None

    def handle_msg(self, body: bytes) -> None:
        mtype: str = body[0:1].decode()  # first char should be printable

        if mtype == "Z" and len(body) > 1:
            self.udlpasswd = body[1:].rstrip(b"\00").decode()
            print(f"detected UDL password {self.udlpasswd}")


def panel_from_ser2net_trace(
    stream: Iterable[str], debug: bool = False, verbose: bool = False
) -> PanelDecoder | None:
    term = SerialWintexPanel(direction="term", debug=debug, verbose=verbose)
    tcp = SerialWintexIgnore(direction="tcp", debug=debug, verbose=verbose)

    buffers = {"tcp": tcp, "term": term}
    for line in stream:
        # 2018/07/31 08:30:59 tcp  03 5a a2                 |.Z.|
        # datetime = line[0:19]
        direction = line[20:25].strip()
        if direction not in buffers:
            continue
        hexbytes = line[25:50].strip().split(" ")
        # if args.debug:
        #    print(f"in: {datetime}' '{direction}' {hexbytes}")
        # decode bytes from hexbytes and push to buffer
        buf = buffers[direction]
        buf.on_bytes(bytes.fromhex("".join(hexbytes)))

    return term.panel


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--verbose", help="Print instructions", action="store_true", default=False
    )
    parser.add_argument(
        "--debug", help="Print bytes on wire", action="store_true", default=False
    )
    parser.add_argument(
        "--mem",
        help="write observations to MEMFILE",
        default=DEFAULT_MEMFILE,
    )
    parser.add_argument(
        "--json", help="dump json extracted data", default=False, action="store_true"
    )
    parser.add_argument("trace", help="Read from ser2net trace files", default="-")

    args = parser.parse_args()

    stream = sys.stdin if args.trace == "-" else open(args.trace, "r")

    panel = panel_from_ser2net_trace(stream)

    if not panel:
        print("error: panel type not determined -- incomplete trace?")
        exit(-1)

    if args.json:
        print(json.dumps(panel.decode(), indent=4))

    if args.mem:
        panel.save(args.mem)
