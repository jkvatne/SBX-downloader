# Safeback downloader for SB01 firmware
 
 Author: Jan Kåre Vatne

## Purpose

This is a python downloader for Safeback SB01.
It can be used to update the firmware on SB01 using a serial port.

## Command line parameters
    -h  --help           : Will show this help info
    -f  --file=<file>    : Download hexfile to card. Include path and quote if necessary
    -p  --port=<comport> : Serial port name (defaults to highest port)
    -s  --start          : Start application

## Example
```
python downloader.py -f=sb01b_rev1.0.1.hex -p=COM6
```
If the com port is not given, the highest numbered port will be used.


## Development environment
Python 3.8 or later. Developed using PyCharm.
Anaconda 3.8 is recommended.

## Dependencies
PySerial