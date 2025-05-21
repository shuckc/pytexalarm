from __future__ import annotations

import argparse
import json
from typing import cast

from scapy.all import PcapNgReader
from scapy.layers.inet import IP, TCP

from . import DEFAULT_MEMFILE
from .pialarm import PanelDecoder
from .trace_uart import SerialWintexIgnore, SerialWintexPanel
from .udl import compact_ranges


def extract_tcp_udl_streams(
    pcapng_path: str,
    src_ip: str,
    dst_ip: str,
    udl_port: int,
    verbose: bool = False,
) -> PanelDecoder | None:
    """
    Reads a pcapng file and extracts TCP payload bytes for both directions
    between (src_ip, src_port) and (dst_ip, dst_port).
    Returns a tuple (client_bytes, server_bytes).
    """
    term = SerialWintexPanel(direction="term", verbose=verbose)
    tcps = SerialWintexIgnore(direction="tcp", verbose=verbose)

    # this assumes one UDL serial message fits in a single packet, ie
    # no payloads split over a TCP packet. We can change this parse to use
    # a pair of buffers and peek the length
    with PcapNgReader(pcapng_path) as pcap:
        for pkt in pcap:
            # ensure we have IP/TCP layers
            if IP not in pkt and TCP not in pkt:  # type: ignore[comparison-overlap]
                continue
            tcp = cast(TCP, pkt[TCP])

            if tcp.dport == udl_port:
                # client → server
                if len(tcp.payload) > 0:
                    tcps.on_bytes(tcp.payload.load)

            elif tcp.sport == udl_port:
                # server → client
                if len(tcp.payload) > 0:
                    term.on_bytes(tcp.payload.load)

            else:
                print(f"Not UDL port: {tcp}")

    # we learn udlpasswd from client side of the conversation
    if term.panel and tcps.udlpasswd:
        term.panel.udlpasswd = tcps.udlpasswd

    if verbose:
        print("Raw read ranges:")
        print(term.mem_ranges)
        print("Compacted read ranges:")
        print(compact_ranges(term.mem_ranges))

    return term.panel


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract UDL stream payloads from pcapng"
    )
    parser.add_argument("pcapng_file", help="Path to .pcapng file")
    parser.add_argument("--src-ip", help="Client IP address")
    parser.add_argument("--dst-ip", help="Server IP address")
    parser.add_argument("--udl-port", type=int, default=10001, help="UDL port")
    parser.add_argument(
        "--mem",
        help="write observations to MEMFILE",
        default=DEFAULT_MEMFILE,
    )
    parser.add_argument(
        "--json", help="dump json extracted data", default=False, action="store_true"
    )
    parser.add_argument(
        "--verbose", help="Print instructions", action="store_true", default=False
    )

    args = parser.parse_args()

    panel = extract_tcp_udl_streams(
        args.pcapng_file, args.src_ip, args.dst_ip, args.udl_port, verbose=args.verbose
    )

    if panel is None:
        exit(-1)

    if args.json:
        print(json.dumps(panel.decode(), indent=4))

    if args.mem:
        panel.save(args.mem)


if __name__ == "__main__":
    main()
