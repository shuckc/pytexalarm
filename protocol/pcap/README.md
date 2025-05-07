Wireshark/tcpdump of Wintex sessions
----------

Start a capture using `tcpdump`, then open up Wintex and connect to the panel, fetch data then disconnect:

    sudo tcpdump --nano -w protocol/pcap/chris-zones.pcapng -s0 tcp port 10001

You can then extract a panel memory dump from the UDL traces with:

    python -m pytexalarm.trace_pcap protocol/pcap/chris-zones.pcapng --json --verbose --mem mypanel.dump

This will attempt to dump the panel memory using the existing decoder class. If you improve the decoders, you can then see the improvment with:

    python -m  pytexalarm.decode --mem mypanel.dump

