## Protocol Traces
Texecom protocol examples, from serial traces captured using logic analyser.
You can open the log files using the Salae Logic software from https://www.saleae.com/downloads/

![Screenshot of logic traces](logic-screenshot.png)

Put the COM port on the panel into 'nothing connected' mode. Like this the panel waits for incoming commands on any of the supported protocols.


Later captures were done by using the built in logger mode of ser2net and pointing wintex at the ser2net port.,

* Simple Protocol - see below
* Wintex protocol - see [wintex-protocol.md](wintex-protocol.md)
* Cestron protocol -

## Simple Protocol

Simple Protocol inputs are wrapped in `\` and `/` characters, responses are terminated with `\r\n`.

Downloading alarm log data.

    <  \W12345678/
    >  OK\r\n
    <  \I/
    >  Elite 24.    ENG->WS V4.02.01LS1\r\n
    <  \X3[0x01]/
    >  Master  0x221 Vx 0x01 0x00 ? 0x00 0x00 0x00 0xFF 0xFF 0xFF 0xFF 0x135 0x177 \r\n
    <  \G0/
    >  0x181 0x01 \r\n
    <  \G2 0x180 0x01 /
    >  12:29.01 01/02. Area: A. PROG.vEND\r\n
    <  \G2 0x179 0x01 /
    ...
    <  \G2 0x178 0x01 /
    ...
    <  \G2 0x163 0x01 /
    >  12:13.19 01/02. Area: AB User000 Engineer\r\n


After re-init panel

    > \G0/
    < 0x141 0x00 \r\n
    > \G2 0x140 0x00 /


Wierd login


    <  \W12345678/
    >  OK\r\n
    <  \X3[0x01]/
    >  Master  0x221 Vx 0x01 0x00 ? 0x00 0x00 0x00 0xFF 0xFF 0xFF 0xFF 0x135 0x177 \r\n
    <  \X3


Logging into panel as engineer

    <  \W12345678/
    >  OK\r\n
    <  \I/
    >  Elite 24.    ENG->WS V4.02.01LS1\r\n
    <  \X3[0x01]/
    >  Master  0x221 Vx 0x01 0x00 ? 0x00 0x00 0x00 0xFF 0xFF 0xFF 0xFF 0x135 0x177 \r\n

    < \L/
    >  System Alerts! 12:45.56 Thu 01 \r\n
    < \L/     polls screen - repeat as required

Keycode using virtual keypad

    < \K 0x01 0x01 /
    > OK\r\n
    < \K 0x01 0x02 /
    > OK \r\n
    < \K 0x01 0x03 /
    > OK \r\n
    < \K 0x01 0x04
    > OK \r\n
    < \L/

    < \K 0x01 0x023 /
    > OK \r\n

2nd login

    < \L/
    > YES to Select:- Zone Setup      \r\n
    <

Keypad additional keys

    \K 0x01 0x08 /
    \K 0x01 0x0D /
    \K 0x01 0x0A /
    \K 0x01 0x0F /


    menu  0x0C
    back  0x15
    area  0x10
    part  0x0E
    chime 0x14
    omit  0x08
    up    0x17
    down


Arm disarm

    < \OP 0xFF 0x02 /
    < \OP 0xFF 0x01 /


X10 Outputs
    < \O?/                repeated query
    > 0x03 0x00 \r\n      response

    < \OX 0xFF 0x01 /       toggle output?
    < OK\r\n
