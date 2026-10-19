"""Application-only programming engine. No bootloader erase or write."""
import hashlib
import json
import os
import struct
from datetime import datetime
from pathlib import Path
from gateway_link import BASE, APP, PAGE

def sha(data): return hashlib.sha256(data).hexdigest()

def validate_image(data, size):
    if not 8 <= len(data) <= size-2048:
        raise ValueError(f'BIN is {len(data)} bytes; this gadget allows 8 to {size-2048} bytes.')
    sp, reset = struct.unpack_from('<II', data)
    if not 0x20000000 < sp <= 0x20001000 or sp % 4:
        raise ValueError('BIN does not begin with a plausible gadget application vector table.')
    if not reset & 1 or not APP <= (reset & ~1) < APP+len(data):
        raise ValueError('BIN reset vector is outside this image at 0x08000800. Rebuild for the application address.')
    return sp, reset

def read_flash(link, size, progress, twice=False):
    result=bytearray()
    for off in range(0,size,64):
        block=link.read(BASE+off,64)
        if twice and link.read(BASE+off,64)!=block:
            raise RuntimeError(f'Repeated read mismatch at 0x{BASE+off:08X}; stopped.')
        result.extend(block)
        progress((off+64)/size)
    return bytes(result)

def save_backup(parent, data, port):
    folder=Path(parent)/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder.mkdir(parents=True,exist_ok=False)
    path=folder/'original.bin'
    with path.open('xb') as f:
        f.write(data);f.flush();os.fsync(f.fileno())
    report={'format':'CJP-GUI-backup-v1','file':'original.bin','size':len(data),
            'sha256':sha(data),'bootloader_sha256':sha(data[:2048]),
            'base':BASE,'application':APP,'port':port,
            'created':datetime.now().astimezone().isoformat()}
    manifest=folder/'backup.json'
    with manifest.open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2);f.flush();os.fsync(f.fileno())
    if path.read_bytes()!=data:
        raise RuntimeError('Saved backup verification failed; no programming allowed.')
    return manifest

def load_backup(manifest):
    manifest=Path(manifest)
    r=json.loads(manifest.read_text(encoding='utf-8'))
    if r.get('format')!='CJP-GUI-backup-v1' or r.get('file')!='original.bin':
        raise ValueError('Select a backup.json created by this GUI.')
    data=(manifest.parent/'original.bin').read_bytes()
    if len(data) not in (16384,32768) or len(data)!=r['size'] or sha(data)!=r['sha256']:
        raise ValueError('Backup integrity check failed.')
    return data

def make_target(current, image):
    validate_image(image,len(current))
    target=bytearray(current)
    target[2048:2048+len(image)]=image
    return bytes(target)

def program(link, current, target, log, progress, stopped=lambda:False):
    if len(target)!=len(current) or len(target) not in (16384,32768):
        raise ValueError('Invalid flash size.')
    if target[:2048]!=current[:2048]:
        raise ValueError('Bootloader change refused.')
    # Force a real programming operation, including when the BIN already matches.
    pages=list(range(2,len(target)//PAGE))
    for i,page in enumerate(pages):
        if stopped(): raise RuntimeError('Stopped between pages. Restore the saved backup before using this gadget.')
        address=BASE+page*PAGE
        wanted=target[page*PAGE:(page+1)*PAGE]
        log(f'Erasing application page {page}...')
        link.erase(page)
        blank=b''.join(link.read(address+o,64) for o in range(0,PAGE,64))
        if blank!=b'\xff'*PAGE: raise RuntimeError(f'Page {page} erase verification failed.')
        for off in range(0,PAGE,64):
            block=wanted[off:off+64]
            if block!=b'\xff'*64: link.write(address+off,block)
        actual=b''.join(link.read(address+o,64) for o in range(0,PAGE,64))
        if actual!=wanted: raise RuntimeError(f'Page {page} readback verification failed.')
        log(f'Page {page}: erased, written and verified.')
        progress((i+1)/len(pages))
    actual=read_flash(link,len(target),lambda _:None)
    if actual!=target: raise RuntimeError('Full flash verification failed.')
    log('FULL_FLASH_VERIFIED; BOOTLOADER_UNCHANGED; SHA256='+sha(actual))
