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
