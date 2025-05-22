from __future__ import annotations

import inspect
import io
import pickle
from enum import Flag, auto
from typing import Any, List, Tuple

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession

from .udl import UDLClient, uncompact_ranges


# configuraable things that you can read or write somewhat atomicaly
# from the panel
class UDLTopics(Flag):
    ZONES = auto()
    AREAS = auto()
    GLOBAL = auto()
    KEYPADS = auto()
    EXPANDERS = auto()
    OUTPUTS = auto()
    COMMS = auto()
    USERS = auto()
    LOGS = auto()
    ALL = ZONES | AREAS | GLOBAL | KEYPADS | EXPANDERS | OUTPUTS | COMMS | USERS | LOGS


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

    async def udl_read_with(self, client: UDLClient, topics: UDLTopics) -> None:
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

    def udl_reads_for(self, topics: UDLTopics) -> List[Tuple[int, int]]:
        # common reads (unique ID)
        reads = [
            (25755, 16),
            (23812, 16),
            (5752, 1),
            (8138, 7),
            (5758, 1),
            (23637, 2),
            (23639, 2),
        ]

        if UDLTopics.ZONES in topics:
            reads.extend(
                [
                    (0, 24),
                    (48, 24),
                    (96, 24),
                    (144, 24),
                    (192, 48),
                    (21504, 768),
                    (2496, 160),
                    (1768, 16),
                    (21280, 100),
                    (2408, 48),
                    (1800, 24),
                    (23468, 24),
                    (20970, 48),
                    (23837, 204),
                ]
            )
        if UDLTopics.AREAS in topics:
            reads.extend([(3144, 512), (5792, 256), (6192, 32), (1512, 32)])

        if UDLTopics.GLOBAL in topics:
            reads.extend(
                [
                    (4128, 400),
                    (6128, 64),
                    (23086, 32),
                    (6992, 32),
                    (6769, 1),
                    (6769, 1),
                    (8064, 64),
                    (288, 96),
                    (5784, 4),
                    (8143, 1),
                    (8143, 1),
                    (3143, 1),
                    (25704, 51),
                    (25771, 17),
                    (8144, 1),
                    (8134, 1),
                    (8135, 1),
                ]
            )

        if UDLTopics.KEYPADS in topics:
            reads.extend([(4000, 128)])

        if UDLTopics.EXPANDERS in topics:
            reads.extend([(3664, 336), (6784, 240), (2496, 160), (2408, 48)])

        if UDLTopics.OUTPUTS in topics:
            reads.extend(
                [(4528, 880), (23040, 40), (6528, 495), (14128, 208), (2408, 48)]
            )

        if UDLTopics.COMMS in topics:
            reads.extend(
                [
                    (5408, 384),
                    (6048, 80),
                    (3416, 6),
                    (3422, 6),
                    (3428, 6),
                    (3434, 6),
                    (3440, 6),
                    (23080, 6),
                    (23119, 149),
                    (6608, 415),
                    (2656, 96),
                    (21184, 96),
                    (23118, 1),
                    (23653, 136),
                    (23828, 1),
                    (23828, 1),
                    (25755, 16),
                    (23812, 16),
                ]
            )

        if UDLTopics.USERS in topics:
            reads.extend(
                [
                    (16384, 200),
                    (17134, 50),
                    (17234, 50),
                    (17334, 25),
                    (17384, 25),
                    (6320, 50),
                    (23268, 25),
                    (16784, 75),
                    (25355, 24),
                    (16934, 100),
                    (2496, 160),
                    (21280, 100),
                ]
            )

        if UDLTopics.LOGS in topics:
            reads.extend([(8190, 2), (8192, 4000)])

        return reads

    async def udl_read_with(self, client: UDLClient, topics: UDLTopics) -> None:
        # do the work
        for base, sz in uncompact_ranges(self.udl_reads_for(topics)):
            bs = await client.read_mem(base, sz)
            self.mem[base : base + sz] = bs


async def interactive_shell(panel: PanelDecoder, **kwargs: Any) -> None:
    """
    Provides a simple repl that allows interactive
    modification of the panel memory.
    """
    with patch_stdout():
        session: PromptSession[str] = PromptSession("(eval) > ")

        # Run echo loop. Read text from stdin, and reply it back.
        while True:
            try:
                pinput = await session.prompt_async()
                r = eval(pinput, {"panel": panel, **kwargs})
                if r:
                    if inspect.isawaitable(r):
                        print("got coro")
                        print(await r)
                    else:
                        print(r)
            except (EOFError, KeyboardInterrupt):
                return
            except Exception as ex:
                print(str(ex))
