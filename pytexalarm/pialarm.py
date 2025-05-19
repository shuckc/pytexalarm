from __future__ import annotations
from typing import Any
import pickle
import io


def printable(c: int, alt: str | None = None) -> str:  # c should be int 0..255
    if alt is None:
        alt = "0x{:02x}".format(c)
    return chr(c) if str.isprintable(chr(c)) else alt


# speak the UDL low-level protocol. Recieve frames in 'on_byes', buffer until the next header's length
# is available, validate CRC and then pass to parse_msg. If a reply is produced, add length prefix and CRC
# then pass this to subclass 'send_bytes'.
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
            chk = self.checksum(self.buf[0:sz])
            if chk != 0:
                print(f"Warning: bad checksum for {self.direction} at {self.buf}")
                # recover from 'ATZ\r' if found
                try:
                    rpos = self.buf.index(b"ATZ\r")
                    print(f"removing before index {rpos}")
                    del self.buf[: rpos + 4]
                except ValueError:
                    print("emptying buffer")
                    del self.buf[:]
            else:
                reply = self.parse_msg(
                    self.buf[1 : sz - 1]
                )  # parser does not need length or checksum
                if reply:
                    msg = bytearray()
                    msg.insert(0, len(reply) + 2)  # prepend size, len(msg)+chk+sz
                    msg.extend(reply)
                    checksum = self.checksum(msg)
                    msg.append(checksum)
                    self.send_bytes(msg)
                del self.buf[0:sz]

    def checksum(self, msg: bytes) -> int:
        # subtract each byte from 0xff
        v = 255
        for b in msg:
            v -= b
        return v % 256

    def log_msg(self, msg: bytes) -> None:
        mtype = msg[0]
        printable_type = printable(mtype)
        msg_hex = " ".join("{:02x}".format(m) for m in msg[1:])
        msg_ascii = "".join(printable(c, alt=".") for c in msg[1:])
        if self.verbose:
            print(f"  {self.direction:4s} {printable_type} {msg_hex} | {msg_ascii} ")

    def parse_msg(self, msg: bytes) -> bytes | None:
        self.log_msg(msg)
        reply = self.handle_msg(msg)
        if reply:
            self.log_msg(reply)
        return reply

    def handle_msg(self, body: bytes) -> bytes | None:
        # subclass for handling logic
        raise ValueError()

    def send_bytes(self, msg: bytes) -> None:
        # optional subclass if sending replies
        pass


class UDLClient:
    pass


FILE_MAGIC = b"pytexalarm\n"
FILE_VERSION = b"1"


class PanelDecoder:
    def __init__(self, banner: str, memsz: int, iosz: int):
        self.mem = bytearray(memsz)
        self.io = bytearray(iosz)
        self.banner: str = banner
        self.serial: str = ""
        self.udlpasswd: str = ""

    def save(self, filename: str) -> None:
        with open(filename, "wb") as f:
            f.write(FILE_MAGIC)
            f.write(FILE_VERSION)
            pickle.dump(self.banner, f, pickle.HIGHEST_PROTOCOL)
            pickle.dump(self.serial, f, pickle.HIGHEST_PROTOCOL)
            pickle.dump(self.udlpasswd, f, pickle.HIGHEST_PROTOCOL)
            pickle.dump(self.mem, f, pickle.HIGHEST_PROTOCOL)
            pickle.dump(self.io, f, pickle.HIGHEST_PROTOCOL)
        print(f"wrote to {filename}")

    def load(self, f: io.BufferedReader) -> None:
        self.serial = pickle.load(f)
        self.udlpasswd = pickle.load(f)
        self.mem = pickle.load(f)
        self.io = pickle.load(f)

    def decode(self) -> dict[str, Any]:
        return {}

    def get_mem(self) -> bytes:
        return self.mem

    def get_io(self) -> bytes:
        return self.io

    def udl_read_with(self, client: UDLClient) -> None:
        pass


def get_panel_decoder(banner: str) -> PanelDecoder:
    # Add extra panels here
    if banner.startswith("Elite 24"):
        return WintexEliteDecoder(banner, 24)
    else:
        # guess at something that might work
        print(f"Unknown panel type {banner} - using large empty default")
        return PanelDecoder(banner, 0x80000, 0x20000)


def panel_from_file(filename: str) -> PanelDecoder:
    print(f"reading panel from {filename}")
    with open(filename, "rb") as w:
        magic = w.read(len(FILE_MAGIC))
        if magic != FILE_MAGIC:
            raise Exception("Unsuported file format")
        version = w.read(len(FILE_VERSION))
        if version != FILE_VERSION:
            raise Exception("Unsuported file version")
        banner: str = pickle.load(w)
        panel = get_panel_decoder(banner)
        panel.load(w)
    return panel


def get_bcd(mem: bytes, start: int, sz: int) -> str:
    rgn = mem[start : start + sz]
    return "".join(["{:01x}".format(x) for x in rgn])


def get_ascii(mem: bytes, start: int, sz: int) -> str:
    rgn = mem[start : start + sz].strip(b"\000")
    return "".join([chr(x) for x in rgn])


class WintexEliteDecoder(PanelDecoder):
    def __init__(self, banner: str, zones: int):
        # Probably these can be determined from the panel type. These work for
        # a Premier Elite 24
        super().__init__(banner, 0x8000, 0x2000)
        self.zones = zones
        self.users = 25
        self.expanders = 2
        self.keypads = 4
        self.areas = 2

    def decode(self) -> dict[str, Any]:
        js: dict[str, Any] = {}
        js["zones"] = self.decode_zones()
        js["users"] = self.decode_users()
        js["areas"] = self.decode_areas()
        js["config"] = {
            "unique_id": get_bcd(self.mem, 0x005D04, 0x10),
            "engineer_reset": get_ascii(self.mem, 0x001100, 32),
            "anticode_reset": get_ascii(self.mem, 0x001120, 32),
            "service_message": get_ascii(self.mem, 0x001140, 32),
            "panel_location": get_ascii(self.mem, 0x001160, 32),
            "banner_message": get_ascii(self.mem, 0x001180, 16),
            "part_arm_header": get_ascii(self.mem, 0x001190, 16),
            "part_arm1_message": get_ascii(self.mem, 0x001800, 16),
            "part_arm2_message": get_ascii(self.mem, 0x001810, 16),
            "part_arm3_message": get_ascii(self.mem, 0x001820, 16),
        }
        js["area_suites"] = self.decode_area_suites()
        js["expanders"] = self.decode_expanders()
        js["enums"] = {
            "zones.type": {
                "type": "lookup",
                "key": "int1",
                "values": [
                    "Entry/Exit 1",
                    "Entry/Exit 2",
                    "Guard",
                    "Guard Access",
                    "24hr Audible",
                    "24hr Silent",
                    "PA Audible",
                    "PA Silent",
                    "Fire",
                    "Medical",
                    "24hr Gas",
                    "Auxilary",
                    "Tamper",
                    "Exit Terminator",
                    "Moment Key",
                    "Latch Key",
                    "Security",
                    "Omit Key",
                    "Custom",
                    "Conf PA Audible",
                    "Conf PA Silent",
                ],
            },
            "zones.wiring": {
                "type": "lookup",
                "key": "int0",
                "values": [
                    "Normally Closed",
                    "Normally Open",
                    "Double Pole/EOL",
                    "Tripple EOL",
                    "1K/1K/(3K)",
                    "4K7/6K8/(12K)",
                    "2K2/4K7/(6K8)",
                    "4K7/4K7",
                    "WD Monitor",
                ],
            },
            "zones.access_areas": {
                "type": "bitmask",
                "values": ["A", "B"],
            },
            "keypad.leds": {
                "type": "bitmask",
                "values": ["?", "?", "Omit"],
            },
        }
        js["communications"] = {
            "sms_centre1": get_ascii(self.mem, 0x001A30, 16),
            "sms_centre2": get_ascii(self.mem, 0x001A40, 16),
        }
        js["virtualkeypad"] = {
            "screen": get_ascii(self.io, 0x001196, 16),
            "screen2": get_ascii(self.io, 0x0011A6, 16),
            "leds": self.io[0x11B7],
        }
        js["keypads"] = self.decode_keypads()
        return js

    def decode_users(self) -> list[dict[str, Any]]:
        users = []
        # merge pincode buffers
        pincode = (
            self.mem[0x004190 : 0x004190 + 0x4B] + self.mem[0x00630B : 0x00630B + 0x18]
        )
        for i in range(self.users):
            users.append(
                {
                    "name": get_ascii(self.mem, 0x004000 + 8 * i, 8).rstrip(),
                    "pincode": self.get_pincode(pincode, 3 * i),
                    "access_areas": self.mem[0x0042EE + i * 2],
                    "flags0": "{:02x}".format(self.mem[0x0042B6 + i]),
                    "flags1": "{:02x}".format(self.mem[0x0043E8 + i]),
                }
            )
        return users

    def decode_zones(self) -> list[dict[str, Any]]:
        zones = []
        for i in range(self.zones):
            zones.append(
                {
                    "name": get_ascii(self.mem, 0x005400 + i * 32, 16),
                    "name2": get_ascii(self.mem, 0x005400 + i * 32 + 16, 16),
                    "type": self.mem[0 + i],
                    "chime": self.mem[0x000030 + i],  # 00 off, 01, 02, 03 chime type
                    "area": self.mem[0x000060 + i],
                    "wiring": self.mem[0x000090 + i],
                    "attrib1": self.mem[0x0000C0 + i * 2],  # omittable bit 0
                    "attrib2": self.mem[0x0000C1 + i * 2],  # double-kock bit 0
                }
            )
        return zones

    def decode_areas(self) -> list[dict[str, Any]]:
        areas = []
        for i in range(self.areas):
            areas.append(
                {
                    "text": get_ascii(self.mem, 0x0016A0 + i * 16, 16),
                }
            )
        return areas

    def decode_expanders(self) -> list[dict[str, Any]]:
        expanders = []
        # sounds is a bitmask, aux_input select byte value,
        # net expander area   aux_input sounds speaker_vol
        # 1   1        000f50 000f70    000f80 000f90
        # 1   2.       000f52 000f71    000f81 000f91
        for i in range(self.expanders):
            expanders.append(
                {
                    "location": get_ascii(self.mem, 0x000E50 + i * 16, 16),
                    "area": self.mem[0x000F50 + i * 2],
                    "aux_input": self.mem[0x000F70 + i],
                    "sounds": self.mem[0x000F80 + i],
                    "speaker": self.mem[0x000F90 + i],
                }
            )
        return expanders

    def decode_keypads(self) -> list[dict[str, Any]]:
        expanders = []
        # zones are literal bytes, volumne is displayed +1 in UI,
        # area are usual bitmask, sounds and options are bitmasks,
        # notes are in the GUI only.
        # net, keypad, zone 1, zone 2, volume, area,   sounds,  options
        #   1.    1.   000fc0, 000fc1, 001000, 000fa0, 001010,  000fe0
        #   1     2.   000fc2, 000fc3, 001001, 000fa2, 001011,  000fe2
        for i in range(self.keypads):
            expanders.append(
                {
                    "keypad_z1_zone": self.mem[0x000FC0 + i * 2],
                    "keypad_z2_zone": self.mem[0x000FC1 + i * 2],
                    "areas": self.mem[0x000FA0 + i * 2],
                    "options": self.mem[0x000FE0 + i * 2],
                    "sounds": self.mem[0x001010 + i],
                    "volume": self.mem[0x001000 + i],
                }
            )
        return expanders

    def decode_area_suites(self) -> list[dict[str, Any]]:
        suites = []
        for i in range(2):
            suites.append(
                {
                    "id": i,
                    "text": get_ascii(self.mem, 0x0005E8 + i * 16, 16),
                    "arm_mode": "",
                    "areas": "",
                }
            )
        return suites

    def get_pincode(self, mem: bytes, offset: int) -> str:
        x = mem[offset : offset + 3]
        return x.hex().strip("def")
