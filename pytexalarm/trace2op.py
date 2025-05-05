import argparse
import sys
import json
import os

from pialarm import SerialWintex, MemStore, WintexMemDecoder

# reads a ser2net trace files from stdin and prints the high-level operations.
# Optionally writes the implied contents of panel mamory to MEMFILE
# verifies serial checksums in the trace
# e.g. $ cat traces/wintex-ser2net/*.trace | python3.6 trace2op.py --mem blob.mem

MEMFILE = os.path.expanduser(os.path.join("~", "alarmpanel.cfg"))

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    "--verbose", help="Print instructions", action="store_true", default=False
)
parser.add_argument(
    "--debug", help="Print bytes on wire", action="store_true", default=False
)
parser.add_argument(
    "--mem", help="write observed values to MEMFILE in position", default=MEMFILE
)
parser.add_argument(
    "--json", help="dump json extracted data", default=False, action="store_true"
)
parser.add_argument("trace", help="Read from ser2net trace files", default="-")


class SerialWintexRecord(SerialWintex):
    def handle_msg(self, mtype, body):
        # commands we will store and destination region
        parts = {("term", "I"): self.mem, ("term", "W"): self.io}
        c = parts.get((self.direction, mtype), None)
        if c:
            base = (body[0] << 16) + (body[1] << 8) + body[2]
            sz = body[3]
            payload = body[4:]
            if sz + 4 != len(body):
                raise Exception("IO length byte does not match msg payload sz")
            c[base] = payload
            print(f"storing msg {mtype} payload={payload} to {base:02x}")
        else:
            print(f"ignoring msg {self.direction}/{mtype} {body}")
        return None


if __name__ == "__main__":
    args = parser.parse_args()

    stream = sys.stdin if args.trace == "-" else open(args.trace, "r")

    with (
        MemStore(args.mem, size=0x8000, file_offset=0x0) as wr_mem,
        MemStore(args.mem, size=0x4000, file_offset=0x8000) as wr_io,
    ):
        buffers = dict(
            [
                (direction, SerialWintexRecord(args, direction, mem=wr_mem, io=wr_io))
                for direction in ["tcp", "term"]
            ]
        )
        for line in stream:
            # 2018/07/31 08:30:59 tcp  03 5a a2                 |.Z.|
            datetime = line[0:19]
            direction = line[20:25].strip()
            if direction not in buffers:
                continue
            hexbytes = line[25:50].strip().split(" ")
            if args.debug:
                print(f"in: {datetime}' '{direction}' {hexbytes}")
            # decode bytes from hexbytes and push to buffer
            buf = buffers[direction]
            for reply in buf.on_bytes([int(x, 16) for x in hexbytes], datetime):
                pass

        if args.json:
            dec = WintexMemDecoder(wr_mem, wr_io)
            print(json.dumps(dec.decode(), indent=4))
