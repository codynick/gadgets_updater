"""Recognize verified bootloader images without modifying device flash."""
import hashlib
import sys
from pathlib import Path

ORIGINAL_SHA='bc7dec5d694bba178dd8948b314ad2c66be008a9ba74382d1dc0f0f53fce7e1c'
K6_IMAGE_SHA='f4dbe08c81b4dff655667181befd782b797aa6ed08e26aff5cd8fbb31bc26d52'
ASSETS=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))

def load_k6(path=None):
    path=Path(path) if path else ASSETS/'bootloader_profiles/stm32f030k6.hex'
    memory={};upper=0;eof=False
    for number,line in enumerate(path.read_text(encoding='ascii').splitlines(),1):
        if not line.strip():continue
        if eof or not line.startswith(':'):raise ValueError(f'Invalid HEX record at line {number}')
        row=bytes.fromhex(line[1:])
        if len(row)<5 or len(row)!=row[0]+5 or sum(row)&255:
            raise ValueError(f'HEX length/checksum error at line {number}')
        address=int.from_bytes(row[1:3],'big');kind=row[3];data=row[4:-1]
        if kind==0:
            for i,value in enumerate(data):
                a=upper+address+i
                if not 0x08000000<=a<0x08000800 or a in memory:
                    raise ValueError('Bootloader HEX address/overlap error')
                memory[a]=value
        elif kind==4 and len(data)==2 and address==0:upper=int.from_bytes(data,'big')<<16
        elif kind==5 and len(data)==4 and address==0:pass
        elif kind==1 and not data and address==0:eof=True
        else:raise ValueError('Unsupported bootloader HEX record')
    if not eof or sorted(memory)!=list(range(0x08000000,0x08000520)):
        raise ValueError('Unexpected supplied K6 bootloader extent')
    image=bytes(memory[a] for a in sorted(memory))
    if hashlib.sha256(image).hexdigest()!=K6_IMAGE_SHA:
        raise ValueError('Supplied K6 bootloader profile integrity check failed')
    return image

def identify_bootloader(block,original_sha=ORIGINAL_SHA):
    if len(block)!=2048:raise ValueError('Expected the complete reserved 2 KB bootloader area')
    if hashlib.sha256(block).hexdigest()==original_sha:
        return 'Original verified gadget bootloader (complete 2 KB match)'
    image=load_k6()
    if block[:len(image)]==image:
        return 'Supplied STM32F030K6 bootloader (all 1312 defined HEX bytes match)'
    return None

def mismatch_summary(block):
    image=load_k6()
    differences=[i for i,value in enumerate(image) if block[i]!=value]
    lines=[f'Compared with supplied K6 HEX: {len(differences)} differing bytes out of {len(image)}.']
    for i in differences[:8]:
        lines.append(f'0x{0x08000000+i:08X}: HEX={image[i]:02X}, device={block[i]:02X}')
    return '\n'.join(lines)
