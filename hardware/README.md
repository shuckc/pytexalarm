
# Wiring Diagram

## Power
I wasn't sure if the communications +12V pins were protected by the texecom polyfuses or montored
for faults, so I've used the power supplies marked DC+/DC- adjacent to the battery connections since
this is likely a very short PCB trace. There is a 7805CT 1A linear regulator on-board, but this is not
suited to power the Pi. The Hobbywing UBEC is a reasonable low-cost DC-DC convertor, easily bought via. ebay such as https://www.ebay.co.uk/itm/Hobbywing-3A-UBEC-5V-6V-Switch-Mode-BEC-/221655594331


    Panel                           Raspberry Pi
                +------------+      GPIO Header P1
    DC+  12V ---| Hobbywing  |----- pin 1   +5V
    DC-   0V ---| 3A 5V UBEC |----- pin 3    0V
                +------------+

The UBEC seems to be regulated to 5.25V, it measures the same under load as open circuit. Note that
powering the PI via. the GPIO pins bypasses the PI polyfuse, so be careful to protect the board traces
from conductive tools etc.

## Communications
I've wired up the com ports on the board to GPIO pins. COM1 gets the 'hardware' UART on the PI, since it
is used for the UDL connections which need to be resillient. The others are bit-banged
on general IO pins using the pigpio libraries emulated uart.

    Panel                                     Raspberry Pi
    COM1 "No device"                          GPIO Header P1
        12v  |o
        -    |x
        0V   |* ---[ 15k ]---\
        Tx   |* -------------*-----
        Rx   |* -------------------

    COM2 "Cestron"
        12v  |o
        -    |x
        0V   |*  ---[ 15k ]---\
        Tx   |*  -------------*----
        Rx   |*  ------------------

     COM3 aka. Digi-Modem
        12v   o
        -     o
        -     o
        -     o
        -     o
        Tx    o
        Rx    o
        -     o
        -     o

The `Tx` lines seem to be driven to 5.3V and have a series protection resister of 9.1kohm. This was characterised by measuring the voltage accross a known resistance to ground. I recommend the following divider:

       5.3V   o-----[ 9.1k ] ----*-----o  GPIO
                                -+-                    Vout = 5.3 * (15/(9.1+15)) = 5.3*0.623 = 3.29v
                                | | 15k
                                | |
                                -+-
        0V    o------------------|-----o

## 1-Wire
I also wired up a 1-wire pull up resistor on the board for 1-wire devices

