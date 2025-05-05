from collections.abc import Iterable
import array


def printable(c, alt=None):  # c should be int 0..255
    if alt is None:
        alt = "0x{:02x}".format(c)
    return chr(c) if str.isprintable(chr(c)) else alt


class SerialWintex:
    def __init__(self, args, direction, mem=None, io=None):
        self.buf = []
        self.args = args
        self.direction = direction
        self.mem = mem
        self.io = io

    def on_bytes(self, bytes_message, context=None):
        self.buf.extend(bytes_message)
        if self.args.debug:
            print(f" buffer: {self.direction:4s} {self.buf}")
        # have we a full message in this direction
        while len(self.buf) > 0 and len(self.buf) >= self.buf[0]:
            sz = self.buf[0]
            chk = self.checksum(self.buf[0:sz])
            if chk != 0:
                print(
                    f"Warning: bad checksum for {self.direction} at {context} -> {self.buf}, emptying buffer"
                )
                del self.buf[:]
            else:
                reply = self.parse_msg(
                    self.buf[1 : sz - 1]
                )  # parser does not need length or checksum
                if reply:
                    msg = []
                    msg.insert(0, len(reply) + 2)  # prepend size, len(msg)+chk+sz
                    msg.extend(reply)
                    checksum = self.checksum(msg)
                    msg.append(checksum)
                    yield msg
                del self.buf[0:sz]
        return

    def checksum(self, msg):
        # subtract each byte from 0xff
        v = 255
        for b in msg:
            v -= b
        return v % 256

    def log_msg(self, direction, msg):
        mtype = msg[0]
        printable_type = printable(mtype)
        msg_hex = " ".join("{:02x}".format(m) for m in msg[1:])
        msg_ascii = "".join(printable(c, alt=".") for c in msg[1:])
        if self.args.verbose:
            print(f"  {direction:4s} {printable_type} {msg_hex} | {msg_ascii} ")

    def parse_msg(self, msg):
        self.log_msg("<", msg)
        mtype = msg[0]
        printable_type = printable(mtype)
        reply = self.handle_msg(printable_type, msg[1:])
        if reply:
            self.log_msg(">", reply)
        return reply

    def handle_msg(self, mtype, body):
        pass


class MemStore:
    def __init__(self, filename, size=0x0, file_offset=0x0):
        self.backing_file = None
        self.file_offset = file_offset
        self.size = size
        self.backing_array = array.array("B", [0] * size)
        try:
            if filename is None:
                raise RuntimeError("not backed by file")
            self.backing_file = open(filename, mode="rb+")
            self.backing_file.seek(file_offset)
            self.backing_array = array.array("B", [])
            self.backing_array.fromfile(self.backing_file, size)
        except FileNotFoundError:
            self.backing_file = open(filename, mode="wb+")
        except EOFError:
            # file on disk too small, we've also effectively truncated backing_array, oops
            self.backing_array = array.array("B", [0] * size)
        except Exception as e:
            raise e

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.backing_file:
            print(
                f"Writing 0x{self.size:x} bytes to offet 0x{self.file_offset:x} within {self.backing_file}"
            )
            self.backing_file.seek(self.file_offset)
            self.backing_array.tofile(self.backing_file)
            self.backing_file.close()

    def __getitem__(self, key):
        return self.backing_array[key]

    def __setitem__(self, key, value):
        # if key > self.size:
        # 	raise IndexError('position {:x} is beyond size={:x}'.format(key, self.size))
        if isinstance(value, Iterable):
            self.backing_array[key : key + len(value)] = array.array("B", value)
        else:
            self.backing_array[key] = value


def get_panel_decoder(args, mem, io):
    if args.panel.startswith("Elite 24"):
        return WintexEliteDecoder(mem, io, 24)
    else:
        return WintexMemDecoder(mem, io)


class WintexMemDecoder:
    pass


class WintexEliteDecoder:
    def __init__(self, mem, io, count=24):
        # Probably these can be determined from the panel type. These work for
        # a Premier Elite 24
        self.zones = 24
        self.users = 25
        self.expanders = 2
        self.keypads = 4
        self.areas = 2
        self.mem = mem
        self.io = io

    def get_ascii(self, mem, start, sz):
        rgn = mem[start : start + sz]
        return "".join([chr(x) for x in rgn])

    def get_bcd(self, mem, start, sz):
        rgn = mem[start : start + sz]
        return "".join(["{:02x}".format(x) for x in rgn])

    def decode(self):
        js = {}
        js["zones"] = self.decode_zones()
        js["users"] = self.decode_users()
        js["areas"] = self.decode_areas()
        js["config"] = {
            "unique_id": self.get_bcd(self.mem, 0x005D04, 0x10),
            "engineer_reset": self.get_ascii(self.mem, 0x001100, 32),
            "anticode_reset": self.get_ascii(self.mem, 0x001120, 32),
            "service_message": self.get_ascii(self.mem, 0x001140, 32),
            "panel_location": self.get_ascii(self.mem, 0x001160, 32),
            "banner_message": self.get_ascii(self.mem, 0x001180, 16),
            "part_arm_header": self.get_ascii(self.mem, 0x001190, 16),
            "part_arm1_message": self.get_ascii(self.mem, 0x001800, 16),
            "part_arm2_message": self.get_ascii(self.mem, 0x001810, 16),
            "part_arm3_message": self.get_ascii(self.mem, 0x001820, 16),
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
            "sms_centre1": self.get_ascii(self.mem, 0x001A30, 16),
            "sms_centre2": self.get_ascii(self.mem, 0x001A40, 16),
        }
        js["virtualkeypad"] = {
            "screen": self.get_ascii(self.io, 0x001196, 16),
            "screen2": self.get_ascii(self.io, 0x0011A6, 16),
            "leds": self.io[0x11B7],
        }
        js["keypads"] = self.decode_keypads()
        return js

    def decode_users(self):
        users = []
        # merge pincode buffers
        pincode = array.array("B", self.mem[0x004190 : 0x004190 + 0x4B])
        pincode.extend(self.mem[0x00630B : 0x00630B + 0x18])
        for i in range(self.users):
            users.append(
                {
                    "name": self.get_ascii(self.mem, 0x004000 + 8 * i, 8).rstrip(),
                    "pincode": self.get_pincode(pincode, 3 * i),
                    "access_areas": self.mem[0x0042EE + i * 2],
                    "flags0": "{:02x}".format(self.mem[0x0042B6 + i]),
                    "flags1": "{:02x}".format(self.mem[0x0043E8 + i]),
                }
            )
        return users

    def decode_zones(self):
        zones = []
        for i in range(self.zones):
            zones.append(
                {
                    "name": self.get_ascii(self.mem, 0x005400 + i * 32, 16),
                    "name2": self.get_ascii(self.mem, 0x005400 + i * 32 + 16, 16),
                    "type": self.mem[0 + i],
                    "chime": self.mem[0x000030 + i],  # 00 off, 01, 02, 03 chime type
                    "area": self.mem[0x000060 + i],
                    "wiring": self.mem[0x000090 + i],
                    "attrib1": self.mem[0x0000C0 + i * 2],  # omittable bit 0
                    "attrib2": self.mem[0x0000C1 + i * 2],  # double-kock bit 0
                }
            )
        return zones

    def decode_areas(self):
        areas = []
        for i in range(self.areas):
            areas.append(
                {
                    "text": self.get_ascii(self.mem, 0x0016A0 + i * 16, 16),
                }
            )
        return areas

    def decode_expanders(self):
        expanders = []
        # sounds is a bitmask, aux_input select byte value,
        # net expander area   aux_input sounds speaker_vol
        # 1   1        000f50 000f70    000f80 000f90
        # 1   2.       000f52 000f71    000f81 000f91
        for i in range(self.expanders):
            expanders.append(
                {
                    "location": self.get_ascii(self.mem, 0x000E50 + i * 16, 16),
                    "area": self.mem[0x000F50 + i * 2],
                    "aux_input": self.mem[0x000F70 + i],
                    "sounds": self.mem[0x000F80 + i],
                    "speaker": self.mem[0x000F90 + i],
                }
            )
        return expanders

    def decode_keypads(self):
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

    def decode_area_suites(self):
        suites = []
        for i in range(2):
            suites.append(
                {
                    "id": i,
                    "text": self.get_ascii(self.mem, 0x0005E8 + i * 16, 16),
                    "arm_mode": "",
                    "areas": "",
                }
            )
        return suites

    def get_pincode(self, mem, offset):
        x = mem[offset : offset + 3].tolist()
        return "{:x}{:x}{:x}".format(*x).strip("def")
