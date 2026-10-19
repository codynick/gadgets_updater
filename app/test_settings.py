import json
import tempfile
import unittest
from pathlib import Path
from settings import load_avrdude,save_avrdude

class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.exe=self.root/'AVR tools/bin/avrdude.exe';self.exe.parent.mkdir(parents=True);self.exe.write_bytes(b'example')
        conf=self.exe.parent.parent/'etc/avrdude.conf';conf.parent.mkdir();conf.write_text('example')
        self.file=self.root/'preferences/settings.json'
    def tearDown(self):self.temp.cleanup()
    def test_saved_custom_path_reused_without_discovery(self):
        save_avrdude(self.file,self.exe)
        def fail():raise AssertionError('Saved valid preference must take priority')
        self.assertEqual(load_avrdude(self.file,fail),str(self.exe.resolve()))
    def test_missing_saved_executable_falls_back(self):
        self.file.parent.mkdir();self.file.write_text(json.dumps({'avrdude_path':str(self.root/'missing.exe')}))
        self.assertEqual(load_avrdude(self.file,lambda:str(self.exe)),str(self.exe))
    def test_corrupt_file_falls_back(self):
        self.file.parent.mkdir();self.file.write_text('{bad json')
        self.assertEqual(load_avrdude(self.file,lambda:str(self.exe)),str(self.exe))
    def test_missing_config_is_not_saved(self):
        (self.exe.parent.parent/'etc/avrdude.conf').unlink()
        with self.assertRaises(ValueError):save_avrdude(self.file,self.exe)
        self.assertFalse(self.file.exists())
    def test_other_preferences_preserved(self):
        self.file.parent.mkdir();self.file.write_text(json.dumps({'another_preference':42}))
        save_avrdude(self.file,self.exe)
        self.assertEqual(json.loads(self.file.read_text())['another_preference'],42)
    def test_missing_settings_and_no_detection_returns_empty(self):
        self.assertEqual(load_avrdude(self.file,lambda:''),'')

if __name__=='__main__':unittest.main()
