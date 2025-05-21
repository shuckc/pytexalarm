import asyncio
from typing import Optional
import argparse

from .udl import udl_frame, udl_verify, UDLClient

from .pialarm import (
    get_bcd,
    get_panel_decoder,
    UDLTopics,
    interactive_shell
)

CMD_LOGIN = 0x5A  # Z
CMD_READ = 0x4F  # 'O'
CMD_RESP = 0x49  # 'I'


class AsyncioUDLClient(UDLClient):
    """
    Asyncio client for Texecom alarm panel protocol.

    Usage:
        client = await AsyncioUDLClient.create('192.168.1.50', 10001)
        model = await client.read_identification()
        print('Panel identification:', model)
        value = await client.read_mem(0x005D04, count=1)
        print(f'Register 0x005D04 = {value.hex()}')
        await client.close()
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        udlpasswd: str,
        serial: Optional[str],
    ):
        self.reader = reader
        self.writer = writer
        self.udlpasswd = udlpasswd
        self.serial = serial

    @classmethod
    async def create(
        cls, host: str, udlpasswd: str, port: int = 10001, serial: Optional[str] = None
    ) -> "AsyncioUDLClient":
        reader, writer = await asyncio.open_connection(host, port)

        instance = cls(reader, writer, udlpasswd, serial)
        return instance

    async def close(self) -> None:
        self.writer.close()
        await self.writer.wait_closed()

    async def do_command(self, msg: bytes) -> bytes:
        await self.send_frame(msg)
        return await self.read_frame()

    async def send_frame(self, msg: bytes) -> None:
        self.writer.write(udl_frame(msg))
        await self.writer.drain()

    async def read_frame(self) -> bytes:
        sz = await self.reader.readexactly(1)
        reply = await self.reader.readexactly(sz[0] - 1)
        if not udl_verify(b"".join([sz, reply])):
            raise ValueError("command reply failed CRC verification")
        return reply[0:-1]

    def _build_mem_io_frame(
        self, cmd: int, addr: int, sz: int = 0, data: bytes = b""
    ) -> bytes:
        # Address is 24-bit
        addr_b1 = (addr >> 16) & 0xFF
        addr_b2 = (addr >> 8) & 0xFF
        addr_b3 = addr & 0xFF
        return bytes([cmd, addr_b1, addr_b2, addr_b3, sz]) + data

    async def read_mem(self, base: int, sz: int) -> bytes:
        """Send a read request and return the data bytes."""
        # split range into 64-byte pages

        print(f" UDL reading base={base} count={sz}")
        frame = self._build_mem_io_frame(CMD_READ, base, sz)
        await self.send_frame(frame)
        resp = await self.read_frame()
        if resp[0] != CMD_RESP:
            raise ValueError(f"Unexpected response code: {resp[0]:02X}")
        assert frame[1:5] == resp[1:5]
        data = resp[5:]
        assert len(data) == sz
        return data

    async def read_identification(self) -> str:
        """After connection, read initial identification text from panel."""
        c = await self.do_command(bytes([CMD_LOGIN]))
        print(f"got serial {get_bcd(c, 1, len(c) - 1)}")
        banner = await self.do_command(bytes([CMD_LOGIN]) + self.udlpasswd.encode())
        return banner[1:].decode()

    async def send_heartbeat(self) -> None:
        hb = await self.do_command(b"P")
        assert hb == b"P\xff\xff"
        return None


async def main() -> None:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--host", help="UDL host/ip", default="localhost")
    parser.add_argument("--password", help="UDL password", default="")
    parser.add_argument("--port", help="UDL port", default=10001, type=int)
    parser.add_argument(
        "--serial", help="expected pannel seral challenge", default=None
    )
    parser.add_argument("--mem", help="write panel config to MEMFILE", default=None)
    args = parser.parse_args()

    client = await AsyncioUDLClient.create(
        args.host, port=args.port, udlpasswd=args.password
    )
    try:
        banner = await client.read_identification()
        print("Banner:", banner)

        await client.send_heartbeat()
        print("got heartbeat")

        panel = get_panel_decoder(banner)

        # Example: read firmware version register
        await panel.udl_read_with(client, UDLTopics.ZONES)
        print("done reads")

        if args.mem:
            panel.save(args.mem)

        try:
            await interactive_shell(panel, client=client, UDLTopics=UDLTopics)
        except Exception as e:
            print(e)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
