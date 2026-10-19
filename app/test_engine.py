import json
import struct
import tempfile
import unittest
from pathlib import Path
from engine import validate_image, make_target, program, save_backup, load_backup, read_flash
from gateway_link import BASE, PAGE

class FakeFlash:
    def __init__(self,data): self.memory=bytearray(data);self.pages=[];self.writes=[];self.fail_erase=False
    def read(self,a,n): return bytes(self.memory[a-BASE:a-BASE+n])
    def erase(self,p):
        assert p>=2
        self.pages.append(p)
        if not self.fail_erase: self.memory[p*PAGE:(p+1)*PAGE]=b'\xff'*PAGE
    def write(self,a,data):
        assert a>=BASE+2048 and a+len(data)<=BASE+len(self.memory)
        self.writes.append(a);self.memory[a-BASE:a-BASE+len(data)]=data

class Tests(unittest.TestCase):
    def setUp(self):
        self.current=bytes((i%251 for i in range(16384)))
        self.image=struct.pack('<II',0x20001000,0x08000841)+b'\x66'*1500
    def test_upgrade_preserves_boot_and_tail(self):
        target=make_target(self.current,self.image);f=FakeFlash(self.current)
        program(f,self.current,target,lambda _:None,lambda _:None)
        self.assertEqual(bytes(f.memory),target)
        self.assertEqual(target[:2048],self.current[:2048])
        self.assertEqual(target[2048+len(self.image):],self.current[2048+len(self.image):])
        self.assertEqual(f.pages,list(range(2,16)))
    def test_identical_image_still_programmed(self):
        target=make_target(self.current,self.image);f=FakeFlash(target)
        program(f,target,target,lambda _:None,lambda _:None)
        self.assertTrue(f.writes);self.assertEqual(f.memory,target)
    def test_restore_damaged_app(self):
        damaged=self.current[:2048]+b'\x00'*(16384-2048);f=FakeFlash(damaged)
        program(f,damaged,self.current,lambda _:None,lambda _:None)
        self.assertEqual(f.memory,self.current)
    def test_boot_change_refused(self):
        target=bytearray(self.current);target[1]^=1;f=FakeFlash(self.current)
        with self.assertRaises(ValueError): program(f,self.current,target,print,print)
        self.assertEqual(f.pages,[])
    def test_linked_at_zero_refused(self):
        image=struct.pack('<II',0x20001000,0x08000101)+b'\x00'*2000
        with self.assertRaises(ValueError): validate_image(image,16384)
    def test_oversize_refused(self):
        with self.assertRaises(ValueError): validate_image(self.image+b'\0'*15000,16384)
    def test_failed_erase_stops(self):
        f=FakeFlash(self.current);f.fail_erase=True
        with self.assertRaises(RuntimeError): program(f,self.current,self.current,lambda _:None,lambda _:None)
        self.assertEqual(f.pages,[2]);self.assertEqual(f.writes,[])
    def test_stop_only_between_pages(self):
        f=FakeFlash(self.current)
        with self.assertRaises(RuntimeError):
            program(f,self.current,self.current,lambda _:None,lambda _:None,lambda:bool(f.pages))
        self.assertEqual(f.pages,[2]);self.assertEqual(f.memory[:3072],self.current[:3072])
    def test_backup_roundtrip_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            manifest=save_backup(d,self.current,'COM6');self.assertEqual(load_backup(manifest),self.current)
            (manifest.parent/'original.bin').write_bytes(b'\0'*16384)
            with self.assertRaises(ValueError): load_backup(manifest)
    def test_repeated_read_mismatch(self):
        class Unstable(FakeFlash):
            def read(self,a,n):
                self.memory[0]^=1
                return super().read(a,n)
        with self.assertRaises(RuntimeError): read_flash(Unstable(self.current),16384,lambda _:None,twice=True)
    def test_32k_bounds(self):
        original=self.current*2;f=FakeFlash(original)
        target=make_target(original,self.image)
        program(f,original,target,lambda _:None,lambda _:None)
        self.assertEqual(f.pages[-1],31);self.assertEqual(f.memory,target)


class WorkflowTests(unittest.TestCase):
    def test_gui_worker_upgrade_and_backup_before_writes(self):
        import app
        import queue
        from unittest.mock import patch
        original=bytes(i%251 for i in range(16384))
        image=struct.pack('<II',0x20001000,0x08000841)+b'\x77'*1500
        with tempfile.TemporaryDirectory() as directory:
            class Transport(FakeFlash):
                def __init__(self,port,log): super().__init__(original);self.closed=False;self.end=BASE+16384
                def open(self): pass
                def request(self,cmd,timeout=0): assert cmd=='H';return b'\x10'
                def erase(self,page):
                    assert list(Path(directory).glob('backups/*/backup.json'))
                    super().erase(page)
                def close(self): self.closed=True
            transport=Transport('',None)
            class Process:
                stdout=['Upload verified\n']
                def __enter__(self): return self
                def __exit__(self,*args): pass
                def wait(self): return 0
            class UI:
                events=queue.Queue()
                import threading
                stop=threading.Event()
                def log(self,x): pass
                def ask(self,*x): pass
                def stage(self,*x): pass
                def progress_value_fallback(self): return 0
            with patch.object(app,'DATA',Path(directory)),patch.object(app,'KNOWN_BOOT_SHA',app.sha(original[:2048])),patch.object(app,'Link',return_value=transport),patch.object(app.subprocess,'Popen',return_value=Process()):
                ui=UI();app.App.worker(ui,'upgrade','COM6',Path('avrdude.exe'),Path('avrdude.conf'),image)
            event,outcome=ui.events.get_nowait()
            self.assertEqual(event,'finish');self.assertTrue(outcome[0],outcome[1]);self.assertTrue(transport.closed)
            self.assertEqual(transport.memory,make_target(original,image))

if __name__=='__main__': unittest.main()
