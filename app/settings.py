"""Per-PC updater preferences, stored outside the Git repository."""
import json
import os
import tempfile
from pathlib import Path

def valid_avrdude(path):
    if not path:return False
    exe=Path(path)
    return exe.is_file() and (exe.parent.parent/'etc/avrdude.conf').is_file()

def load_avrdude(settings_file,discover):
    try:
        data=json.loads(Path(settings_file).read_text(encoding='utf-8'))
        saved=data.get('avrdude_path') if isinstance(data,dict) else None
        if isinstance(saved,str) and valid_avrdude(saved):return saved
    except (OSError,ValueError,TypeError):pass
    found=discover()
    return found if valid_avrdude(found) else ''

def save_avrdude(settings_file,path):
    if not valid_avrdude(path):raise ValueError('AVRDUDE executable or matching configuration is missing.')
    settings_file=Path(settings_file);settings_file.parent.mkdir(parents=True,exist_ok=True)
    try:
        data=json.loads(settings_file.read_text(encoding='utf-8'))
        if not isinstance(data,dict):data={}
    except (OSError,ValueError):data={}
    data['avrdude_path']=str(Path(path).resolve())
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=settings_file.parent,delete=False) as f:
            temporary=Path(f.name);json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(temporary,settings_file)
    finally:
        if temporary and temporary.exists():temporary.unlink()
