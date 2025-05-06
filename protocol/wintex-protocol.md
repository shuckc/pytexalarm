# Wintex captures

    < wintex to panel
    > reply

### Login exchange
UDL password is 12345678, `Elite 24     V4.02.01` is the panel type string seen from simple protocol.

    < 03 5a a2
    > 0b 5a 05 01 00 07 09 04 07 01 78
    < 0b 5a 31 32 33 34 35 36 37 38 f6
    > 17 5a 45 6c 69 74 65 20 32 34 20 20 20 20 56 34 2e 30 32 2e 30 31 ec     .ZElite 24    V4.02.01

The initial reply to `Z` contains a Z, then `05`, then the panel serial number 1 digit BCD per byte `1079471` which allows Wintex to verify it is handing the UDL password over to the correct panel.

### Query/response to read values `07 4f ...` ?

    < 07 4f 00 64 9b 10 9a
    > 17 49 00 64 9b 10 2f fc 56 50 85 90 48 44 76 11 43 39 ce c4 19 76 fa
    < 07 4f 00 5d 04 10 38
    > 17 49 00 5d 04 10 54 01 07 94 71 b6 49 17 a5 1b 32 5a 96 f9 6e 49 25
    < 07 4f 00 16 78 01 1a
    > 08 49 00 16 78 01 06 19
    < 07 4f 00 1f ca 07 b9
    > 0e 49 00 1f ca 07 01 00 00 00 ff ff 2c 8d
    < 07 4f 00 16 7e 01 14
    > 08 49 00 16 7e 01 00 19
    < 07 4f 00 5c 55 02 f6
    > 09 49 00 5c 55 02 f0 59 b1

### Framing
Looks like length prefixed byte, and from last-digit only
differences between request and response, looks like 1-byte checksum

Sample CRC codes `< 03 5a a2`

    03  0000 0011
    5a  0101 1010
    a2  1010 0010

    07 4f 00 64 9b 10 9a

Doesn't look like XOR based.
Look for plaintext with single bit differences between messages:

    $ less tr1 | grep "07 4f" | cut -c 26- | sort -u | uniq
    07 4f 00 20 00 40 49     |.O. .@I|
    07 4f 00 20 40 40 09     |.O. @@.|  adding 40 subtracts 40 from checksum
    ...
    07 4f 00 2b 80 40 be     |.O.+.@.|
    07 4f 00 2b c0 40 7e     |.O.+.@~|  8->c changes b->7
    ..
    07 4f 00 20 80 40 c9     |.O. .@.|
    07 4f 00 20 c0 40 89     |.O. .@.|  8->c changes c->8

Both cases no cascade of changes to other nibble
Looks like subtractions or 2s compliment addition, bytewise
Possible bias or initial value?

    b8 + 5a = a2
    03 - 5a = a9
    0 - 03 -5a = a3
    FF - 03 - 5a = a2  <-- looks good

    FF - 07 -4f -20 - 40 = 49

To verify substract checksum and look for `(x & 0xFF) = 0`
To encode do FF - each byte value then mask 0xFF

First digit is length of message 0-255 bytes, including check digit and size byte. size byte is included in checksum also.

### Ping/pong when idle
Looks like 10-second timer, client initiates and panel responds

    2018/07/23 12:46:12 tcp  03 50 ac                 |.P.|
    2018/07/23 12:46:12 term 05 50 ff ff ac           |.P...|
    2018/07/23 12:46:22 tcp  03 50 ac                 |.P.|
    2018/07/23 12:46:22 term 05 50 ff ff ac           |.P...|
    2018/07/23 12:46:32 tcp  03 50 ac                 |.P.|
    2018/07/23 12:46:32 term 05 50 ff ff ac           |.P...|
    2018/07/23 12:46:42 tcp  03 50 ac                 |.P.|
    2018/07/23 12:46:42 term 05 50 ff ff ac           |.P...|

### Using virtual keypad feature

Command R is answered by W and seems to be screen polling feature of remote keypad system. Unknown what bytes `00 11 96 22` do but they are returned on the answer.

    2018/07/24 12:46:50 tcp  07 52 00 11 96 22 dd     |.R...".|
    2018/07/24 12:46:50 term 29 57 00 11 96 22 20 53  |)W..." S|
    2018/07/24 12:46:50 term 79 73 74 65 6d 20 41 6c  |ystem Al|
    2018/07/24 12:46:50 term 65 72 74 73 21 20 31 33  |erts! 13|
    2018/07/24 12:46:50 term 3a 34 34 2e 33 37 20 54  |:44.37 T|
    2018/07/24 12:46:50 term 75 65 20 32 34 20 00 00  |ue 24 ..|
    2018/07/24 12:46:50 term b3                       |.|
    2018/07/24 12:46:50 tcp  07 52 00 11 96 22 dd     |.R...".|
    2018/07/24 12:46:50 term 29 57 00 11 96 22 20 53  |)W..." S|
    2018/07/24 12:46:50 term 79 73 74 65 6d 20 41 6c  |ystem Al|
    2018/07/24 12:46:50 term 65 72 74 73 21 20 31 33  |erts! 13|
    2018/07/24 12:46:50 term 3a 34 34 2e 33 38 20 54  |:44.38 T|
    2018/07/24 12:46:50 term 75 65 20 32 34 20 00 00  |ue 24 ..|
    2018/07/24 12:46:50 term b2                       |.|
    2018/07/24 12:46:51 tcp  07 52 00 11 96 22 dd     |.R...".|
    2018/07/24 12:46:51 term 29 57 00 11 96 22 20 53  |)W..." S|
    2018/07/24 12:46:51 term 79 73 74 65 6d 20 41 6c  |ystem Al|
    2018/07/24 12:46:51 term 65 72 74 73 21 20 31 33  |erts! 13|
    2018/07/24 12:46:51 term 3a 34 34 2e 33 38 20 54  |:44.38 T|
    2018/07/24 12:46:51 term 75 65 20 32 34 20 00 00  |ue 24 ..|
    2018/07/24 12:46:51 term b2                       |.|

I sent user login of `5678` which seems to be `4b` K messages acked by `06` (stripping screen polling out):

    2018/07/24 12:46:52 tcp  05 4b 01 05 a9           |.K...|
    2018/07/24 12:46:52 term 03 06 f6                 |...|
    ...
    2018/07/24 12:46:52 tcp  05 4b 01 06 a8           |.K...|
    2018/07/24 12:46:52 term 03 06 f6                 |...|
    ...
    2018/07/24 12:46:53 tcp  05 4b 01 07 a7           |.K...|
    2018/07/24 12:46:53 term 03 06 f6                 |...|
    ...
    2018/07/24 12:46:54 tcp  05 4b 01 08 a6           |.K...|
    2018/07/24 12:46:54 term 03 06 f6                 |...|
    2018/07/24 12:46:54 tcp  07 52 00 11 96 22 dd     |.R...".|
    2018/07/24 12:46:54 term 29 57 00 11 96 22 5a 6f  |)W..."Zo|
    2018/07/24 12:46:54 term 6e 65 20 30 30 31 20 54  |ne 001 T|
    2018/07/24 12:46:54 term 61 6d 70 65 72 20 5a 4f  |amper ZO|
    2018/07/24 12:46:54 term 4d 45 30 30 31 61 62 63  |ME001abc|
    2018/07/24 12:46:54 term 64 65 66 67 68 69 00 00  |defghi..|
    2018/07/24 12:46:54 term 67                       |g|


### Message Types

First payload byte seems to be message type
TCP sending R seems to be answered by W, O answered by I
TCP sending W answered by 0x06 ack
P answers P, Z with Z

    4f  O  options/parameters request
    49  I  parameters response
    50  P  ping/pong heartbeat
    5a  Z  authentication
    52  R  screen request
    57  W  screen reply
    4b  K  keypad press
    06  .  keypad/general ack
    48  H  logout
        B  trigger special operation after W write
        U  <n> trigger special operation n

It seems that persistent configuration is read with R/W cycles, and volatile state is examined with O/I cycles.

### R/W cycles
Sometimes R/W is not giving back screen messages. Could be another bus device or something else?  `52 00 11 92 22` keypad
 vs. `52 00 1d f8 40` is this:

    2018/07/23 12:50:45 tcp  07 52 00 1d f8 40 51     |.R...@Q|
    2018/07/23 12:50:45 term 47 57 00 1d f8 40 00 00  |GW...@..|
    2018/07/23 12:50:45 term 00 00 00 00 00 ff ff ff  |........|
    2018/07/23 12:50:45 term ff 00 00 00 00 00 00 00  |........|
    2018/07/23 12:50:45 term 00 00 00 00 ff ff ff ff  |........|
    2018/07/23 12:50:45 term 00 00 00 00 00 00 00 00  |........|
    2018/07/23 12:50:45 term 00 00 00 ff ff ff ff 00  |........|
    2018/07/23 12:50:45 term 00 00 00 00 00 00 00 00  |........|
    2018/07/23 12:50:45 term 00 00 ff ff ff ff 00 00  |........|
    2018/07/23 12:50:45 term 00 00 00 00 00 00 1c     |.......|

If I is sent from wintex to the panel, it always seems to be a block and answered by 0x06, fixed length ack? I think this is pushing configuration.

    2018/07/24 12:43:27 tcp  47 49 00 12 70 40 ff ff  |GI..p@..|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ed     |.......|
    2018/07/24 12:43:28 term 03 06 f6                 |...|


### O/I cycles - memory read and values
Looks like the protocol is not so much an "API" to the panel features, but a way to read and write raw bytes to the configuration memory. The *O* requests specify and _offset_ and _size_ within the configuration, and the
*I* response returns _size_ bytes from that _offset_. Offsets of 0x40, 0x30, 0x18 are quite common.

The recording were taken on a 24 zone panel, lots of the reads are for 0x18 (24) bytes, so it seems each feature of a zone might be stored at a different base address, allowing code to be shared with the 48, 96 zone panels.

Following table summarised from `$ cat zones.trace | grep "tcp" | grep "07 4f" | cut -c 26- | sort` and simialr:

    offset     size*reads  trace     purpose
    0x000000   0x18 * 1    zones     24* byte, zone type
    0x000030   0x18 * 1    zones     24* byte, zone chime
    0x000060   0x18 * 1    zones     24* byte, zone area, bitmask ABCDEF...
    0x000090   0x18 * 1    zones     24* byte, zone wiring (perhaps)
    0x0000c0   0x30 * 1    zones     possible zone attributes?
    0x0006e8   0x10 * 1    zones     ?
    0x000708   0x18 * 1    zones     24* byte, not sure, all 0x00
    0x000968   0x30 * 1    zones     ?
    0x0009c0   0x40 * 1    zones     ?
    0x000a00   0x40 * 2    zones     ?
    0x000e50                         expander location text 2x16 bytes
    0x001100                         system LCD messages
    0x0011d0                         ?  24*4 byte values, repeats xx020300
    0x001a30                         communicator SMS numbers
    0x001678   0x01 * 1    zones     ?  always 0x06
    0x00167e   0x01 * 1    zones     ?
    0x001800                         part arm names
    0x001fca   0x07 * 1    rc        ? always 0x01 00 00 00 ff ff 2c
    0x001fd1   0x2d * 1    dt        serial number, then config?
    0x004000   0x40*3+0x08 users     usernames - 200 bytes: 25*8-byte
    0x004190   0x40+0x0b   users     user pin codes (1/2) - 25*3-bytes
    0x0042ee   0x32        users     user type 0x0300 engineer, 0x0100 master,...
    0x0043b6   0x19        users     user flags?
    0x0043e8   0x19.       users     user flags?
    0x0051ea   0x30 * 1    zones     ?
    0x005320   0x40+0x24   zones     100 bytes
    0x005400   0x40 * 12   zones     24*0x20 byte zone text
    0x005bac   0x18 * 1    zones     24* byte, not sure, all 0x00
    0x005c55   0x02 * 1    zones     ? always 0x28 c0
    0x005d04   0x10 * 1    zones     Engineering Utils -> Unique ID
    0x005d1d   0x40 * 3    zones     ?
    0x005ddd   0x08 * 1    zones     ?
    0x005de5   0x04 * 1    zones     ?
    0x00630b   0x18 * 1    users     user pin codes (2/2) - 25 bytes
    0x00649b   0x10 * 1    zones,all ?

Looks like knowing which regions of the memory can be read is one issue, then decoding the resulting blob of bytes. Trace files are:

    zones       wintex-ser2net/zones.trace
    rc          wintex-ser2net/diagnostics-remote-control.trace
    users       wintex-ser2net/users.trace
    dt          wintex-ser2net/datetime-reset.trace

For 'user pin codes' there are 25x4 bytes in one contiguous section, than another 25 bytes at another location, I suspect pin codes were increased from 4 digits to 6 digits in some firmware release. Unprogrammed pin codes are written as 0xffeedd (not enterable digits) 4 digit pins have a trailing 0xdd.


### R/W cycles - volaile state

`R` and `W` cycles used to read from and write to volatile state, by the 'diagnostics' commands.

    offset     size*reads  trace      purpose
    0x003069   0x06        dt         real time clock readout
    0x003207   0x02        rc         00 00  timer control + PC control bits
    0x0017b6   0x02        rc         03 00  area state
    0x0017c2   0x04        rc         00 00 00 00    if armed
    0x0017de   0x02        rc         00 00          if reset req?
    0x0017ea   0x02        rc         00 00          if in test
    0x001520   0x20        rc         keypad send message buffer
    0x001196   0x22        kp         keypad read message buffer


### Diagnostics -> PC control, Timer control, Message and arming

    Polls `0x003207` for two bytes, pc control and timer control status
    Setting PC control writes bitwise output latch to 0x003208

    pccontrol 1 activate, writes 0x01 to 0x003208 for 0x01
       reads back at 0x003207 0x02   value as written 0x01
    pc control 2 activated, writes 0x02 to 0x003208 for 0x01
    pc control 3 activated, writes 0x04 to 0x003208 for 0x01
    pc control 4 activates, writes 0x08 to 0x003208 for 0x01

    Timer control writes to upper byte `0x003207

   Sending a messages to keypads writes 0x20 bytes ascii to `0x001520` then triggers
   special op `U 0x40`

   Arming dropdown area A, 'Full Arm' sends A 0x00, after a few seconds
     0x0017c2 changes from 0x00000000 to 0x01000000
   Sending disarm sends D 0x000, clears 0x0017c2

   Part Arm 1 sends `S 00 01`, 0x0017c2 shows 00000100, disarm same
   Parm arm 2 sends `S 00 02`, 0x0017c2 shows 00000100, disarm same
   Part arm 3 sends `S 00 03`

   Area state ready 0x03, alarm triggered 0x02

   Test sends `C 00`

### Diagnostics -> Keypad

   To poll keypad screen read  0x001196 for 0x22 bytes. Highest 2 bytes
   are status LEDs, 0x04 is probably 'Omit'.

    K 01 15   Reset
    K 01 0c   Menu
    K 01 16   Up
    K 01 17   Down
    K 01 0b   Omit
    K 01 14   Chime
    K 01 0e   Part
    K 01 10   Area
    K 01 0d   Yes
    K 01 0f   No
    K 01 05   1
    K 01 05   2
    K 01 05   3
    K 01 05   4
    K 01 05   5
    K 01 06   6
    K 01 07   7
    K 01 08   8
    K 01 09   9
    K 01 0a   0



