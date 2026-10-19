import json
import struct
import tempfile
import unittest
from pathlib import Path
from firmware_store import add_file, add_bytes, scan

class FirmwareStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.folder=self.root/'firmware'
        self.image=struct.pack('<II',0x20001000,0x08000841)+b'\x55'*1500
    def tearDown(self): self.temp.cleanup()
    def test_import_copies_original_and_records_hash(self):
        source=self.root/'display v1.bin';source.write_bytes(self.image)
        path,created=add_file(self.folder,source)
        self.assertTrue(created);self.assertEqual(source.read_bytes(),self.image)
        self.assertEqual(path.read_bytes(),self.image)
        rows=scan(self.folder);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['error'],'')
        self.assertIn('not been verified',rows[0]['notes'])
        self.assertEqual(rows[0]['size'],1508)
    def test_duplicate_contents_reuses_entry(self):
        first,_=add_bytes(self.folder,'one.bin',self.image)
        second,created=add_bytes(self.folder,'two.bin',self.image)
        self.assertFalse(created);self.assertEqual(first,second)
        self.assertEqual(len(list(self.folder.glob('*.bin'))),1)
    def test_same_name_different_contents_retains_both(self):
        first,_=add_bytes(self.folder,'one.bin',self.image)
        other=self.image[:-1]+b'\x66'
        second,created=add_bytes(self.folder,'one.bin',other)
        self.assertTrue(created);self.assertNotEqual(first,second)
        self.assertEqual(first.read_bytes(),self.image);self.assertEqual(second.read_bytes(),other)
    def test_tampered_bin_invalidates_metadata(self):
        path,_=add_bytes(self.folder,'one.bin',self.image)
        path.write_bytes(self.image[:-1]+b'\x88')
        self.assertIn('checksum',scan(self.folder)[0]['error'])
    def test_invalid_layout_not_copied(self):
        with self.assertRaises(ValueError):add_bytes(self.folder,'wrong.bin',b'\0'*100)
        self.assertFalse(self.folder.exists())
    def test_reserved_windows_name_is_sanitized(self):
        path,_=add_bytes(self.folder,'CON.bin',self.image)
        self.assertTrue(path.name.startswith('firmware_CON__'))
    def test_existing_files_are_not_overwritten(self):
        path,_=add_bytes(self.folder,'one.bin',self.image)
        path.with_suffix('.json').write_text('{invalid')
        other,created=add_bytes(self.folder,'one.bin',self.image)
        self.assertTrue(created);self.assertNotEqual(other,path)
        self.assertEqual(path.with_suffix('.json').read_text(),'{invalid')
    def test_checkbox_off_has_no_import(self):
        import app
        class Value:
            def get(self):return False
        class UI:
            add_to_catalog=Value()
        app.App.add_current_firmware(UI())
        self.assertFalse(self.folder.exists())
    def test_checkbox_on_imports_and_selects_saved_copy(self):
        import app
        from unittest.mock import patch
        source=self.root/'display.bin';source.write_bytes(self.image)
        class Value:
            def __init__(self,value):self.value=value
            def get(self):return self.value
            def set(self,value):self.value=value
        class UI:
            add_to_catalog=Value(True);image=Value(str(source));selected=None
            def refresh_firmware(self,selected=None):self.selected=selected
            def log(self,message):pass
        ui=UI()
        with patch.object(app,'FIRMWARE',self.folder):app.App.add_current_firmware(ui)
        self.assertEqual(Path(ui.image.get()).parent,self.folder)
        self.assertEqual(Path(ui.image.get()),ui.selected)
        self.assertEqual(source.read_bytes(),self.image)
    def test_packaged_sevensegment_metadata(self):
        rows=scan(Path(__file__).resolve().parent.parent/'firmware')
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['size'],12072)
        self.assertEqual(rows[0]['error'],'')

if __name__=='__main__': unittest.main()
