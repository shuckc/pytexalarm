import os

import pytest

from pytexalarm.trace_pcap import extract_tcp_udl_streams
from pytexalarm.trace_uart import panel_from_ser2net_trace


def test_ser2net_trace() -> None:
    with open("protocol/wintex-ser2net/zones.trace", "r") as r:
        panel = panel_from_ser2net_trace(r)

        assert panel is not None
        data = panel.decode()
        assert data["zones"][0]["name"] == "ZOME001abcdefghi"
        assert data["zones"][0]["name2"] == "jklmnopqrstuvwxy"
        assert data["zones"][1]["name"] == "zome002abcdefghi"
        assert data["zones"][1]["name2"] == "jkmnopqrstuvwxyz"
        # inconsisten nulls/spaces in zone names (we truncate nulls)
        assert data["zones"][2]["name"] == "ZOME003"
        assert data["zones"][2]["name2"] == "                "


fn = "protocol/pcap/chris-zones.pcapng"


@pytest.mark.skipif(not os.path.isfile(fn), reason="chris capture not installed")
def test_pcap_trace() -> None:
    # only fetches Zone data in this trace
    panel = extract_tcp_udl_streams(fn, "", "", 10001)
    assert panel is not None
    data = panel.decode()
    assert data["zones"][0]["name"] == "Z1"
    assert data["zones"][1]["name"] == "Z2"
    assert data["zones"][2]["name"] == ""
    assert data["zones"][3]["name"] == "Bottom Stair PIR"
    assert data["zones"][4]["name"] == "Boot Room PIR"
    assert data["zones"][5]["name"] == "Kitchen PIR"
    assert data["zones"][6]["name"] == "Lounge PIR"
    assert data["zones"][7]["name"] == "Bedroom PIR"
    assert data["zones"][8]["name"] == "Stairs Top PIR"
    assert data["zones"][9]["name"] == "Boot Room Door"
