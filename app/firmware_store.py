"""Local firmware catalog. Imports never overwrite an existing BIN."""
import json
import os
import re
from pathlib import Path
from datetime import datetime
from engine import sha, validate_image

def scan(folder):
    rows=[]
    folder=Path(folder)
    if not folder.exists(): return rows
    for path in sorted(folder.glob('*.bin'),key=lambda p:p.name.casefold()):
        if path.is_symlink(): continue
        row={'path':path,'name':path.stem,'error':'','notes':''}
        try:
            data=path.read_bytes();validate_image(data,32768)
            row.update(size=len(data),sha256=sha(data))
            metadata=path.with_suffix('.json')
            if metadata.exists():
                report=json.loads(metadata.read_text(encoding='utf-8'))
                if not isinstance(report,dict) or report.get('sha256')!=row['sha256']:
                    raise ValueError('Metadata checksum does not match the BIN.')
                row['name']=str(report.get('name') or path.stem)
                row['notes']=str(report.get('notes') or '')
        except Exception as exc: row['error']=str(exc)
        rows.append(row)
    return rows

def add_bytes(folder, filename, data):
    """Validate the captured bytes; deduplicate by content; preserve existing files."""
    validate_image(data,32768)
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    checksum=sha(data)
    for row in scan(folder):
        if row.get('sha256')==checksum and not row['error']:
            return row['path'],False
    stem=re.sub(r'[^A-Za-z0-9._-]+','_',Path(filename).stem).strip('._-')[:70] or 'firmware'
    if stem.upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
        stem='firmware_'+stem
    candidate=folder/(stem+'__'+checksum[:12]+'.bin')
    number=1
    while candidate.exists() or candidate.with_suffix('.json').exists():
        candidate=folder/(stem+'__'+checksum[:12]+f'_{number}.bin');number+=1
    # Exclusive creation: collisions cannot replace an existing version.
    with candidate.open('xb') as f:
        f.write(data);f.flush();os.fsync(f.fileno())
    if candidate.read_bytes()!=data: raise RuntimeError('Imported BIN verification failed.')
    metadata={'name':Path(filename).stem,'sha256':checksum,'size':len(data),
              'application_address':'0x08000800',
              'added':datetime.now().astimezone().isoformat(),
              'notes':'Imported locally. Gadget compatibility and runtime operation have not been verified.'}
    with candidate.with_suffix('.json').open('x',encoding='utf-8') as f:
        json.dump(metadata,f,indent=2,ensure_ascii=False);f.write('\n');f.flush();os.fsync(f.fileno())
    return candidate,True

def add_file(folder, source):
    source=Path(source)
    if source.suffix.lower()!='.bin': raise ValueError('Select an application .bin file.')
    return add_bytes(folder,source.name,source.read_bytes())
