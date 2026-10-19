"""CJP v5 serial transport. Main flash only; bootloader writes rejected."""
import argparse
import binascii
import hashlib
import json
import struct
import sys
import time
from datetime import datetime
from pathlib import Path
import serial

BASE = 0x08000000
APP = BASE + 0x800
END = BASE + 0x4000
PAGE = 1024
ROOT = Path(__file__).resolve().parent

def digest(data):
    return hashlib.sha256(data).hexdigest()

def check_range(address, count, writing=False, end=END):
    low = APP if writing else BASE
    if not 1 <= count <= 64 or not low <= address <= end - count:
        raise ValueError('Address/length outside permitted main-flash range')
    if writing and (address % 4 or count % 4):
        raise ValueError('Writes must be aligned to four bytes')

def packet(seq, cmd, payload=b''):
    body = bytes([seq, ord(cmd), len(payload)]) + payload
    if len(payload) > 68:
        raise ValueError('Packet too large')
    return b'\xc3\x5a' + body + struct.pack('>H', binascii.crc_hqx(body, 0xffff))

class Link:
    def __init__(self, port, log):
        self.log = log
        self.seq = 0
        self.end = END
        self.serial = serial.Serial(port=None, baudrate=9600, parity=serial.PARITY_NONE,
                                    timeout=0.1, write_timeout=3)
        self.serial.port = port
        self.serial.dtr = False
        self.serial.rts = False

    def open(self):
        self.serial.open()
        self.serial.dtr = True
        time.sleep(0.2)
        self.serial.dtr = False
        time.sleep(2)
        banner = self.serial.read(self.serial.in_waiting).decode('ascii', errors='replace').strip()
        if banner:
            self.log(banner)
        if self.request('P') != b'CJP5':
            raise RuntimeError('Gateway v5 was not identified')
        self.log('PC_GATEWAY_OK')

    def exact(self, count, deadline):
        data = bytearray()
        while len(data) < count:
            if time.monotonic() >= deadline:
                raise TimeoutError('Gateway response timeout; no automatic write retry')
            data.extend(self.serial.read(count-len(data)))
        return bytes(data)

    def request(self, cmd, payload=b'', timeout=10):
        self.seq = (self.seq + 1) & 255
        self.serial.write(packet(self.seq, cmd, payload))
        self.serial.flush()
        deadline = time.monotonic() + timeout
        text = bytearray()
        while True:
            b = self.exact(1, deadline)
            if b == b'\x3c':
                if self.exact(1, deadline) != b'\xa5':
                    raise RuntimeError('Invalid response prefix')
                break
            text.extend(b)
            if b == b'\n':
                self.log(text.decode('ascii', errors='replace').strip())
                text.clear()
        header = self.exact(4, deadline)
        seq, command, status, length = header
        if length > 64:
            raise RuntimeError('Invalid response length')
        result = self.exact(length, deadline)
        crc = struct.unpack('>H', self.exact(2, deadline))[0]
        if binascii.crc_hqx(header+result, 0xffff) != crc:
            raise RuntimeError('Response CRC mismatch; stopped')
        if seq != self.seq or command != ord(cmd):
            raise RuntimeError('Response sequence/command mismatch')
        if status:
            raise RuntimeError(f'Gateway rejected/failed {cmd}, status={status}. Stop and reconnect before recovery.')
        return result

    def read(self, address, count):
        check_range(address, count, end=self.end)
        result = self.request('R', struct.pack('>IB', address, count))
        if len(result) != count:
            raise RuntimeError('Short read')
        return result

    def erase(self, page):
        if not 2 <= page < (self.end-BASE)//PAGE:
            raise ValueError('Bootloader/out-of-range page rejected')
        if self.request('E', bytes([page]), timeout=20) != bytes([page]):
            raise RuntimeError('Erase response mismatch')

    def write(self, address, data):
        check_range(address, len(data), writing=True, end=self.end)
        result = self.request('W', struct.pack('>I', address)+data)
        if result != struct.pack('>I', address):
            raise RuntimeError('Write response mismatch')

    def close(self):
        self.serial.close()

def read_area(link, address, length, log, label):
    data = bytearray()
    for off in range(0, length, 64):
        data.extend(link.read(address+off, min(64, length-off)))
        if len(data) % 2048 == 0 or len(data) == length:
            log(f'{label}: {len(data)}/{length} bytes')
    return bytes(data)

