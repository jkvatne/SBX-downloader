# Copyright (c) 2005-2012, Alexander Belchenko
# All rights reserved.
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided
# that the following conditions are met:
#
# * Redistributions of source code must retain
#   the above copyright notice, this list of conditions
#   and the following disclaimer.
# * Redistributions in binary form must reproduce
#   the above copyright notice, this list of conditions
#   and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of the author nor the names
#   of its contributors may be used to endorse
#   or promote products derived from this software
#   without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Intel HEX file format reader and converter.

@author     Alexander Belchenko (bialix AT ukr net)
@version    1.4
Modified by Jan Kåre Vatne
"""
from array import array
from binascii import unhexlify


class IntelHex(object):
    """ Intel HEX file reader. """

    def __init__(self, source=None):
        """ Constructor. If source specified, object will be initialized
        with the contents of source. Otherwise the object will be empty.

        @param  source      source for initialization
                            (file name of HEX file, file object, addr dict or
                             other IntelHex object)
        """
        # public members
        self.padding = 0x0FF
        # Start Address
        self.start_addr = None

        # private members
        self._buf = {}
        self._offset = 0
        self.loadhex(source)

    def size(self):
        return len(self._buf)

    def _decode_record(self, s, line=0):
        """Decode one record of HEX file.

        @param  s       line with HEX record.
        @param  line    line number (for error messages).

        @raise  EndOfFile   if EOF record encountered.
        """
        s = s.rstrip('\r\n')
        if not s:
            return  # empty line

        if s[0] == ':':
            try:
                bin = array('B', unhexlify(s[1:]))
            except (TypeError, ValueError):
                # this might be raised by unhexlify when odd hexascii digits
                raise HexRecordError(line=line)
            length = len(bin)
            if length < 5:
                raise HexRecordError(line=line)
        else:
            raise HexRecordError(line=line)

        record_length = bin[0]
        if length != (5 + record_length):
            raise RecordLengthError(line=line)

        addr = bin[1] * 256 + bin[2]

        record_type = bin[3]
        if not (0 <= record_type <= 5):
            raise RecordTypeError(line=line)

        crc = sum(bin)
        crc &= 0x0FF
        if crc != 0:
            raise RecordChecksumError(line=line)

        if record_type == 0:
            # data record
            addr += self._offset
            for i in range(4, 4 + record_length):
                if not self._buf.get(addr, None) is None:
                    raise AddressOverlapError(address=addr, line=line)
                self._buf[addr] = bin[i]
                addr += 1  # FIXME: addr should be wrapped
                # BUT after 02 record (at 64K boundary)
                # and after 04 record (at 4G boundary)

        elif record_type == 1:
            # end of file record
            if record_length != 0:
                raise EOFRecordError(line=line)
            raise _EndOfFile

        elif record_type == 2:
            # Extended 8086 Segment Record
            if record_length != 2 or addr != 0:
                raise ExtendedSegmentAddressRecordError(line=line)
            self._offset = (bin[4] * 256 + bin[5]) * 16

        elif record_type == 4:
            # Extended Linear Address Record
            if record_length != 2 or addr != 0:
                raise ExtendedLinearAddressRecordError(line=line)
            self._offset = (bin[4] * 256 + bin[5]) * 65536

        elif record_type == 3:
            # Start Segment Address Record
            if record_length != 4 or addr != 0:
                raise StartSegmentAddressRecordError(line=line)
            if self.start_addr:
                raise DuplicateStartAddressRecordError(line=line)
            self.start_addr = {'CS': bin[4] * 256 + bin[5],
                               'IP': bin[6] * 256 + bin[7],
                               }

        elif record_type == 5:
            # Start Linear Address Record
            if record_length != 4 or addr != 0:
                raise StartLinearAddressRecordError(line=line)
            if self.start_addr:
                raise DuplicateStartAddressRecordError(line=line)
            self.start_addr = {'EIP': (bin[4] * 16777216 +
                                       bin[5] * 65536 +
                                       bin[6] * 256 +
                                       bin[7]),
                               }

    def loadhex(self, fobj):
        """Load hex file into internal buffer. This is not necessary
        if object was initialized with source set. This will overwrite
        addresses if object was already initialized.

        @param  fobj        file name or file-like object
        """
        if getattr(fobj, "read", None) is None:
            fobj = open(fobj, "r")
            fclose = fobj.close
        else:
            fclose = None

        self._offset = 0
        line = 0

        try:
            decode = self._decode_record
            try:
                for s in fobj:
                    line += 1
                    decode(s, line)
            except _EndOfFile:
                pass
        finally:
            if fclose:
                fclose()

    def __getitem__(self, addr):
        """ Get requested byte from address.
        @param  addr    address of byte.
        @return         byte if address exists in HEX file, or self.padding
                        if no data found.
        """
        if addr < 0:
            raise TypeError('Address should be >= 0.')
        return self._buf.get(addr, self.padding)


class IntelHexError(Exception):
    """Base Exception class for IntelHex module"""

    _fmt = 'IntelHex base error'  #: format string

    def __init__(self, msg=None, **kw):
        """Initialize the Exception with the given message.
        """
        self.msg = msg
        for key, value in kw.items():
            setattr(self, key, value)

    def __str__(self):
        """Return the message in this Exception."""
        if self.msg:
            return self.msg
        try:
            return self._fmt % self.__dict__
        except (NameError, ValueError, KeyError) as e:
            return 'Unprintable exception %s: %s' \
                   % (repr(e), str(e))


class _EndOfFile(IntelHexError):
    """Used for internal needs only."""
    _fmt = 'EOF record reached -- signal to stop read file'


class HexReaderError(IntelHexError):
    _fmt = 'Hex reader base error'


class AddressOverlapError(HexReaderError):
    _fmt = 'Hex file has data overlap at address 0x%(address)X on line %(line)d'


# class NotAHexFileError was removed in trunk.revno.54 because it's not used


class HexRecordError(HexReaderError):
    _fmt = 'Hex file contains invalid record at line %(line)d'


class RecordLengthError(HexRecordError):
    _fmt = 'Record at line %(line)d has invalid length'


class RecordTypeError(HexRecordError):
    _fmt = 'Record at line %(line)d has invalid record type'


class RecordChecksumError(HexRecordError):
    _fmt = 'Record at line %(line)d has invalid checksum'


class EOFRecordError(HexRecordError):
    _fmt = 'File has invalid End-of-File record'


class ExtendedAddressRecordError(HexRecordError):
    _fmt = 'Base class for extended address exceptions'


class ExtendedSegmentAddressRecordError(ExtendedAddressRecordError):
    _fmt = 'Invalid Extended Segment Address Record at line %(line)d'


class ExtendedLinearAddressRecordError(ExtendedAddressRecordError):
    _fmt = 'Invalid Extended Linear Address Record at line %(line)d'


class StartAddressRecordError(HexRecordError):
    _fmt = 'Base class for start address exceptions'


class StartSegmentAddressRecordError(StartAddressRecordError):
    _fmt = 'Invalid Start Segment Address Record at line %(line)d'


class StartLinearAddressRecordError(StartAddressRecordError):
    _fmt = 'Invalid Start Linear Address Record at line %(line)d'


class DuplicateStartAddressRecordError(StartAddressRecordError):
    _fmt = 'Start Address Record appears twice at line %(line)d'


class InvalidStartAddressValueError(StartAddressRecordError):
    _fmt = 'Invalid start address value: %(start_addr)s'


def main():
    print("Test intelhex.py by reading test.hex")
    try:
        h = IntelHex('test.hex')
        print("Length=%d"%(h.size()))
        print(hex(h[0]))
        print(hex(h[1]))
        print(hex(h[2]))
    except IntelHexError as err:
        print("ERROR: ", err)
    except IOError as err:
        print("ERROR: ", err)


if __name__ == '__main__':
    main()
