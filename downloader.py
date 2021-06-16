# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:        downloader.py
# Author:      Jan Kåre Vatne
# Created:     11.06.2021
# -------------------------------------------------------------------------------
import signal
import time
import sys
import serial
import getopt
import traceback
import ports
import intelhex
from datetime import datetime

ERASE_CMD = 0x45
ADR_CMD = 0x85
DATA_CMD1 = 0xC7
DATA_CMD2 = 0xCD
DATA_CMD3 = 0xD3
DATA_CMD4 = 0xD9
AUX_CMD = 0x02
CRC_CMD = 0x01
START_CMD = 0x02
REV_CMD = 0x03
READ_WORD = 0x04
READ_DWORD = 0x05
OK_RESP = 0x0A
ERR_RESP = 0xAA
QUERY_CMD = 0x61


class SB01(object):

    def __init__(self, port_name):
        self.com = serial.Serial(port_name, baudrate=19200)
        self.com.timeout = 0.5
        self.is_open = True
        self.current_address = 0
        self.com.flushInput()

    def erase(self, a):
        self.com.flushInput()
        self.com.write(bytes([ERASE_CMD, a & 0xFF, (a >> 8) & 0xFF, (a >> 16) & 0xFF, (a >> 24) & 0xFF]))
        resp = self.com.read(1)
        if resp[0] != OK_RESP:
            raise Exception("Erase 0x%X failed, got %s" % (a, str(resp)))

    def write6(self, d0, d1, d2, d3, d4, d5):
        self.com.write(bytes([DATA_CMD1, d0, d1, d2, d3, d4, d5]))
        resp = self.com.read(1)
        if resp[0] != OK_RESP:
            raise Exception("Write data failed, adr = {:04X}".format(self.current_address))
        if len(resp) > 3:
            print("write() returned current_address = {:02X} {:02X} {:02X}".format(resp[1], resp[2], resp[3]))
        self.current_address = self.current_address + 4

    def exit_bootloader(self):
        self.com.flushInput()
        self.com.write(bytes([AUX_CMD, START_CMD]))

    def get_crc(self):
        self.com.flushInput()
        self.com.write(bytes([AUX_CMD, CRC_CMD]))
        resp = self.com.read(2)
        if len(resp) != 2:
            print("Get crc failed")
        else:
            print("Crc=%x" % resp)

    def get_rev(self):
        self.com.flushInput()
        self.com.write(bytes([AUX_CMD, REV_CMD]))
        resp = self.com.read(2)
        if len(resp) != 2:
            print("Get revision failed")
        else:
            print("Bootloader revision %d.%d" % (resp[0], resp[1]))
        return resp

    def set_adr(self, a):
        self.current_address = a
        self.com.write(bytes([ADR_CMD, a & 0xFF, (a >> 8) & 0xFF, (a >> 16) & 0xFF, (a >> 24) & 0xFF]))
        resp = self.com.read(1)
        return resp == b'\n'

    def read_word(self):
        self.com.write(bytes([AUX_CMD, READ_WORD]))
        resp = self.com.read(4)
        self.current_address = self.current_address + 2
        return resp

    def read_dword(self):
        self.current_address = self.current_address + 4
        self.com.write(bytes([AUX_CMD, READ_DWORD]))
        resp = self.com.read(8)
        return resp

    def verify(self, data):
        r = self.read_word()
        d = data.to_bytes(4, byteorder='little')
        if r[0] != d[0] or r[1] != d[1] or r[2] != d[2]:
            print("Verify failed")
            print("Expected {:02X} {:02X} {:02X}".format(d[0], d[1], d[2]))
            print("Got      {:02X} {:02X} {:02X}".format(r[0], r[1], r[2]))
            sys.exit(1)


def exit_gracefully():
    board.exit_bootloader()
    sys.exit(0)


def test(b):
    print("Verify flash 0x0000")
    b.set_adr(0x0000)
    b.verify(0x04A300)
    b.verify(0x000000)
    r = b.read_word()
    print("Data at 0x0004 = {:02X} {:02X} {:02X}".format(r[0], r[1], r[2]))

    print("Test erase page 0")
    b.erase(0x0000)
    print("Verify erased page 0")
    b.set_adr(0x0000)
    b.verify(0x04A300)
    b.verify(0x000000)
    b.verify(0xFFFFFF)

    b.erase(0x1000)
    print("Verify erased")
    b.set_adr(0x1000)
    for i in range(0x80):
        b.verify(0xFFFFFF)
    b.set_adr(0x0000)
    b.verify(0x04A300)
    b.verify(0x000000)

    print("Write data to 0x1000")
    b.set_adr(0x1000)
    b.write6(0x16, 0x17, 0x18, 0x19, 0x20, 0x21)
    b.write6(0x22, 0x23, 0x24, 0x25, 0x26, 0x27)
    print("Verify written data 0x1000")
    b.set_adr(0x1000)
    b.verify(0x181716)
    b.verify(0x212019)
    b.verify(0x242322)
    b.verify(0x272625)
    b.verify(0xFFFFFF)

    print("Verify written data 0x1800")
    b.set_adr(0x1800)
    for i in range(8):
        b.verify(0xFFFFFF)

    print("Test ok")
    sys.exit(0)


if __name__ == '__main__':
    # Catch ctrl-C and exit gracefully
    signal.signal(signal.SIGINT, exit_gracefully)
    start_application = False

    ports = ports.ComPorts()
    print("List of ports ", ports.get_ports()[1:])

    # Get full command-line arguments
    full_cmd_arguments = sys.argv
    # Keep all but the first
    argument_list = full_cmd_arguments[1:]
    try:
        short_options = "hf:p:s"
        long_options = ["help", "file=", "port=", "start"]
        arguments, values = getopt.getopt(argument_list, short_options, long_options)
    except getopt.error as err:
        # Output error, and return with an error code
        print(str(err))
        sys.exit(2)

    hex_file = ""
    port = ""
    for current_argument, current_value in arguments:
        if current_argument in ("-f", "--file"):
            hex_file = current_value
        elif current_argument in ("-p", "--port"):
            port = str.lstrip(current_value, '=:')
        elif current_argument in ("-s", "--start"):
            start_application = True
        else:
            #  current_argument in ("-h", "--help") or any unknown parameter
            print("The following arguments are valid:")
            print("-h  --help           : Will show this help info")
            print("-f  --file=<file>    : Download hex-file to card. Include path and quote if necessary")
            print("-p  --port=<comport> : Serial port name")
            print("-s  --start          : Start application")
            sys.exit(0)

    try:
        start_time = time.time()

        if port == '':
            port = ports.get_default_port_name()

        if port == '' or port is None:
            print("No com-port found")
            sys.exit(1)

        try:
            board = SB01(port)
        except:
            print("Flash programming done. Time used: %d sec" % (time.time() - start_time))
            print("Error opening port \"%s\"" % port)
            sys.exit(1)

        rev = board.get_rev()
        if rev[0] > 1:
            print("This bootloader version is not supported")
            sys.exit(2)

        hex = intelhex.IntelHex(hex_file)

        if start_application:
            board.exit_bootloader()
            sys.exit(0)

        # Erase all
        for adr in range(0x0000, 0x5000, 0x800):
            board.erase(adr)

        # Find last address
        last_adr = 0x5000
        for adr in range(0x5000 - 4, 0x0100, -4):
            b0 = hex[adr * 2 + 0]
            b1 = hex[adr * 2 + 1]
            b2 = hex[adr * 2 + 2]
            b3 = hex[adr * 2 + 4]
            b4 = hex[adr * 2 + 5]
            b5 = hex[adr * 2 + 6]
            if b0 != 0xFF or b1 != 0xFF or b2 != 0xFF or b3 != 0xFF or b4 != 0xFF or b5 != 0xFF:
                last_adr = adr + 4
                break

        print("Last used address in hex file is 0x%X" % last_adr)
        print("Flash programming started at ", datetime.now().strftime("%H:%M:%S"))

        # Write 6 bytes at a time, i.e. 4 words or 2 instructions a 3 bytes.
        # starting at word 4 (instruction 2) which is interrupt vector
        board.set_adr(0x0004)
        for adr in range(0x0004, last_adr, 4):
            b0 = hex[adr * 2 + 0]
            b1 = hex[adr * 2 + 1]
            b2 = hex[adr * 2 + 2]
            b3 = hex[adr * 2 + 4]
            b4 = hex[adr * 2 + 5]
            b5 = hex[adr * 2 + 6]
            board.write6(b0, b1, b2, b3, b4, b5)
            p = int(100 * board.current_address / last_adr)
            print("\r%d%%  " % p, end='', flush=True)
        board.exit_bootloader()
        print("Flash programming done. Time used: %d sec" % (time.time() - start_time))

    except SystemExit as e:
        sys.exit(0)

    except:
        traceback.print_exc(file=sys.stdout)
        sys.exit(3)
