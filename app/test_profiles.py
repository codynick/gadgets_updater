import hashlib
import tempfile
import unittest
from pathlib import Path
from profiles import load_k6, identify_bootloader, mismatch_summary, ORIGINAL_SHA

class BootloaderProfileTests(unittest.TestCase):
    def test_supplied_hex_is_recognized(self):
        image=load_k6();self.assertEqual(len(image),1312)
        self.assertIn('STM32F030K6',identify_bootloader(image+b'\xff'*(2048-len(image))))
    def test_undefined_tail_is_not_inferred_from_hex(self):
        image=load_k6();block=image+bytes(i%256 for i in range(2048-len(image)))
        self.assertIn('STM32F030K6',identify_bootloader(block))
        from engine import make_target
        import struct
        flash=block+b'\x55'*(32768-2048)
        app=struct.pack('<II',0x20001000,0x08000841)+b'\x22'*100
        self.assertEqual(make_target(flash,app)[:2048],block)
    def test_changed_defined_byte_is_refused(self):
        image=bytearray(load_k6());image[0x280]^=1
        block=bytes(image)+b'\xff'*(2048-len(image))
        self.assertIsNone(identify_bootloader(block))
        self.assertIn('0x08000280',mismatch_summary(block))
    def test_explicit_hex_padding_must_match(self):
        image=bytearray(load_k6());image[0x51c]=255
        self.assertIsNone(identify_bootloader(bytes(image)+b'\xff'*(2048-len(image))))
    def test_original_complete_hash_route_retained(self):
        block=b'\x42'*2048
        name=identify_bootloader(block,hashlib.sha256(block).hexdigest())
        self.assertIn('complete 2 KB match',name)
    def test_hex_checksum_tamper_refused(self):
        p=Path(__file__).resolve().parent/'bootloader_profiles/stm32f030k6.hex'
        with tempfile.TemporaryDirectory() as d:
            changed=Path(d)/'bad.hex';changed.write_text(p.read_text().replace('28040020','29040020',1))
            with self.assertRaises(ValueError):load_k6(changed)

class ProfileWorkflowTests(unittest.TestCase):
    def run_workflow(self,mode,recognized):
        import app
        import queue,threading
        from unittest.mock import patch
        from test_engine import FakeFlash
        from gateway_link import BASE
        block=load_k6()+b'\xff'*(2048-1312)
        if not recognized:block=bytes([block[0]^1])+block[1:]
        flash=block+b'\x55'*(32768-2048)
        import struct
        image=struct.pack('<II',0x20001000,0x08000841)+b'\x22'*100
        with tempfile.TemporaryDirectory() as d:
            class Transport(FakeFlash):
                end=BASE+32768
                def open(self):pass
                def close(self):pass
                def request(self,cmd,timeout=0):return b'\x20'
            link=Transport(flash)
            class Process:
                stdout=[]
                def __enter__(self):return self
                def __exit__(self,*a):pass
                def wait(self):return 0
            class UI:
                events=queue.Queue();stop=threading.Event()
                def log(self,t):pass
                def stage(self,*a):pass
                def ask(self,*a):pass
                def progress_value_fallback(self):return 0
            ui=UI()
            with patch.object(app,'DATA',Path(d)),patch.object(app,'Link',return_value=link),patch.object(app.subprocess,'Popen',return_value=Process()):
                app.App.worker(ui,mode,'COM6',Path('avr'),Path('conf'),image)
            backup=list(Path(d).glob('backups/*/original.bin'))
            self.assertEqual(len(backup),1);self.assertEqual(backup[0].read_bytes(),flash)
            event,result=ui.events.get_nowait();self.assertEqual(event,'finish')
            return result,link,flash
    def test_unknown_bootloader_backup_is_readonly_and_succeeds(self):
        result,link,_=self.run_workflow('backup',False)
        self.assertTrue(result[0],result[1]);self.assertEqual(link.pages,[])
    def test_unknown_bootloader_upgrade_saves_backup_then_refuses(self):
        result,link,_=self.run_workflow('upgrade',False)
        self.assertFalse(result[0]);self.assertIn('neither recognized',result[1]);self.assertEqual(link.pages,[])
    def test_k6_upgrade_32k_preserves_bootloader(self):
        result,link,flash=self.run_workflow('upgrade',True)
        self.assertTrue(result[0],result[1]);self.assertEqual(link.pages[-1],31)
        self.assertEqual(link.memory[:2048],flash[:2048])

if __name__=='__main__':unittest.main()
