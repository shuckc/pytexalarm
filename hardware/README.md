
# Wiring Diagram

## Serial RX/TX Wiring
First I used a couple of FTDI USB external COM ports (5V tolerant) as a proof of concept. However it is much neater to omit these and use the GPIO pins on the pi directly. The COM ports on the alarm mainboard all drive `Tx` to 5V logic levels, with a series protection resistor of 9.1kOhm, which needs to be accounted for in the voltage divider to reduce to 3.3V logic for the raspberry pi GPIO pins. Since the protection resistor is quite large, I used this as the top resister in the divider chain, with a bottom resistor of 15kOhm. For Rpi -> Panel, I drove the panel's Rx pin directory with no problems.


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


## Preparing the pi
Install a blank `rasbian` install to an SD Card (ideally skipping NOOBS). Boot using a keyboard and screen, then use `sudo raspi-config` to enable ssh (`5 Interfacing Options` -> `P2 SSH` -> `Yes`) then change the password for the `pi` user using `passwd`.

It is necessary to disable the serial `tty` that raspian attaches to `/dev/ttyACM0` in order to access the hardware UART. With recent rasbian releases it is a simple matter of running `sudo raspi-config` and disabling the serial tty under `5 Interfacing Options` -> `P6 Serial` -> `No` -> `Yes` -> `OK`, giving this summary:

    The serial login shell is disabled
    The serial interface is enabled

Now install the contents of this repository to `~/pialarm` as follows:

    $ sudo apt-get install git
    $ git clone https://github.com/shuckc/pialarm.git
    $ cd pialarm
    $ pip3.6 install -r requirements.txt
    $ python

You may also update the Pi kernel and firmware with `$ sudo rpi-update` - didn't cause any problems for me.
