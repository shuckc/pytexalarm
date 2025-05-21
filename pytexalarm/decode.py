import argparse
import json

from . import DEFAULT_MEMFILE
from .hexdump import hexdump
from .pialarm import panel_from_file

# reads a ser2net trace files from stdin and prints the high-level operations.
# Optionally writes the implied contents of panel memory to MEMFILE
# verifies serial checksums in the trace in both directions
# e.g. $ cat traces/wintex-ser2net/*.trace | python -m pytexalarm.trace2op --mem blob.mem --json

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--mem", help="read saved panel file", default=DEFAULT_MEMFILE)
    parser.add_argument(
        "--json", help="dump json extracted data", default=False, action="store_true"
    )

    args = parser.parse_args()

    panel = panel_from_file(args.mem)

    if not panel:
        print("error: panel type not determined -- incomplete trace?")
        exit(-1)

    if args.json:
        print(json.dumps(panel.decode(), indent=4))

    print("Configuration memory:")
    print(hexdump(panel.get_mem()))

    print("State memory:")
    print(hexdump(panel.get_io()))
