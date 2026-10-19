"""CJP technician updater: Windows GUI, bundled Uno gateway, backup and restore."""
import json
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from serial.tools import list_ports
from gateway_link import BASE, Link
from engine import validate_image, read_flash, save_backup, load_backup, make_target, program, sha
from firmware_store import scan, add_file
from profiles import identify_bootloader, mismatch_summary
from settings import load_avrdude, save_avrdude, valid_avrdude

ASSETS=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
DATA=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'CJP Upgrader'
SETTINGS=DATA/'settings.json'
PROJECT=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent.parent
FIRMWARE=PROJECT/'firmware'

def find_avrdude():
    root=Path(os.environ.get('LOCALAPPDATA',''))/'Arduino15/packages'
    choices=list(root.glob('arduino/tools/avrdude/*/bin/avrdude.exe'))
    choices+=list(root.glob('MiniCore/tools/avrdude/*/bin/avrdude.exe'))
    return next((str(p) for p in reversed(sorted(choices)) if valid_avrdude(p)),'')

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('CodyNick Gadgets Updater v4');self.geometry('1000x810');self.minsize(850,700)
        self.events=queue.Queue();self.busy=False;self.stop=threading.Event();self.logfile=None
        self.port=tk.StringVar();self.image=tk.StringVar();self.avr=tk.StringVar(value=load_avrdude(SETTINGS,find_avrdude))
        self.catalog_choice=tk.StringVar();self.add_to_catalog=tk.BooleanVar(value=False)
        self.firmware_info=tk.StringVar(value='Choose firmware from the local folder or browse a BIN.')
        self.status=tk.StringVar(value='Select the CJP COM port and application BIN.')
        main=ttk.Frame(self,padding=16);main.pack(fill='both',expand=True)
        ttk.Label(main,text='CodyNick Gadgets Updater',font=('Segoe UI',19,'bold')).pack(anchor='w')
        ttk.Label(main,text='Application address: 0x08000800  •  Automatic backup  •  Bootloader preserved').pack(anchor='w',pady=(3,14))
        row=ttk.Frame(main);row.pack(fill='x',pady=4)
        ttk.Label(row,text='CJP port',width=15).pack(side='left')
        self.ports=ttk.Combobox(row,textvariable=self.port,state='readonly',width=45);self.ports.pack(side='left')
        self.refresh_button=ttk.Button(row,text='Refresh',command=self.refresh);self.refresh_button.pack(side='left',padx=8)
        self.edit_buttons=[]
        catalog_row=ttk.Frame(main);catalog_row.pack(fill='x',pady=4)
        ttk.Label(catalog_row,text='Local firmware',width=15).pack(side='left')
        self.catalog=ttk.Combobox(catalog_row,textvariable=self.catalog_choice,state='readonly')
        self.catalog.pack(side='left',fill='x',expand=True)
        self.catalog.bind('<<ComboboxSelected>>',self.choose_firmware)
        refresh_catalog=ttk.Button(catalog_row,text='Refresh list',command=self.refresh_firmware)
        refresh_catalog.pack(side='left',padx=(8,0));self.edit_buttons.append(refresh_catalog)
        for label,var,kind in [('Application BIN',self.image,'bin'),('AVRDUDE',self.avr,'exe')]:
            r=ttk.Frame(main);r.pack(fill='x',pady=4)
            ttk.Label(r,text=label,width=15).pack(side='left')
            e=ttk.Entry(r,textvariable=var,state='readonly' if kind=='bin' else 'normal');e.pack(side='left',fill='x',expand=True)
            if kind=='bin': self.bin_entry=e
            b=ttk.Button(r,text='Browse…',command=lambda v=var,k=kind:self.browse(v,k));b.pack(side='left',padx=(8,0))
            self.edit_buttons.extend([e,b])
        self.add_check=ttk.Checkbutton(main,text='Add browsed BIN to local firmware folder',variable=self.add_to_catalog,command=self.add_current_firmware)
        self.add_check.pack(anchor='w',pady=4);self.edit_buttons.append(self.add_check)
        ttk.Label(main,textvariable=self.firmware_info,wraplength=920).pack(anchor='w',pady=3)
        tools=ttk.Frame(main);tools.pack(fill='x',pady=3)
        open_firmware=ttk.Button(tools,text='Open firmware folder',command=self.open_firmware_folder)
        open_firmware.pack(side='left')
        publish=ttk.Button(tools,text='GitHub push commands…',command=self.open_github)
        publish.pack(side='left',padx=8);self.edit_buttons.extend([open_firmware,publish])
        ttk.Label(main,text='Use an application BIN built for 0x08000800. Layout checks cannot prove firmware compatibility.',wraplength=860).pack(anchor='w',pady=8)
        r=ttk.Frame(main);r.pack(fill='x',pady=8)
        self.actions=[]
        for text,mode in [('Upgrade gadget','upgrade'),('Backup only','backup'),('Restore backup…','restore')]:
            b=ttk.Button(r,text=text,command=lambda m=mode:self.start(m));b.pack(side='left',padx=(0,8));self.actions.append(b)
        self.stop_button=ttk.Button(r,text='Stop after current page',command=self.request_stop,state='disabled');self.stop_button.pack(side='right')
        ttk.Label(main,textvariable=self.status,wraplength=860,font=('Segoe UI',10,'bold')).pack(anchor='w',pady=8)
        self.progress=ttk.Progressbar(main,maximum=100);self.progress.pack(fill='x')
        ttk.Label(main,text='Live terminal log').pack(anchor='w',pady=(12,4))
        terminal=ttk.Frame(main);terminal.pack(fill='both',expand=True)
        self.console=tk.Text(terminal,wrap='word',bg='#14212b',fg='#e0edf5',font=('Consolas',10),state='disabled')
        scroll=ttk.Scrollbar(terminal,command=self.console.yview);self.console.configure(yscrollcommand=scroll.set)
        self.console.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        ttk.Button(main,text='Open backups and logs',command=self.open_data).pack(anchor='e',pady=(8,0))
        self.protocol('WM_DELETE_WINDOW',self.close_app);self.refresh();self.refresh_firmware();self.after(80,self.poll)

    def browse(self,var,kind):
        p=filedialog.askopenfilename(filetypes=[('BIN firmware','*.bin')] if kind=='bin' else [('AVRDUDE','avrdude.exe')])
        if not p: return
        if kind!='bin':
            if not valid_avrdude(p):
                messagebox.showerror('AVRDUDE required','Select avrdude.exe with its matching ../etc/avrdude.conf.',parent=self);return
            var.set(p);self.remember_avrdude(p);return
        try:
            data=Path(p).read_bytes();validate_image(data,32768)
            var.set(p);self.catalog_choice.set('')
            self.firmware_info.set(f'{len(data):,} bytes • External BIN • '+sha(data)[:16])
            self.add_current_firmware()
        except Exception as exc: messagebox.showerror('Cannot select firmware',str(exc),parent=self)

    def refresh_firmware(self,selected=None):
        try:
            rows=scan(FIRMWARE)
            self.firmware_map={f'{r["name"]} — {r["path"].name}'+(' [INVALID]' if r['error'] else ''):r for r in rows}
            self.catalog['values']=list(self.firmware_map)
            match=next((label for label,r in self.firmware_map.items() if selected and r['path'].resolve()==Path(selected).resolve()),None)
            if match: self.catalog_choice.set(match);self.choose_firmware()
            elif self.catalog_choice.get() not in self.firmware_map: self.catalog_choice.set('')
        except Exception as exc: messagebox.showerror('Firmware folder',str(exc),parent=self)

    def remember_avrdude(self,path):
        try: save_avrdude(SETTINGS,path)
        except (OSError,ValueError) as exc:
            messagebox.showwarning('Cannot save AVRDUDE preference','This session can continue, but the path could not be saved:\n'+str(exc),parent=self)

    def choose_firmware(self,event=None):
        row=self.firmware_map.get(self.catalog_choice.get())
        if not row: return
        if row['error']:
            self.image.set('');self.firmware_info.set('Invalid firmware: '+row['error']);return
        self.image.set(str(row['path']))
        self.firmware_info.set(f'{row["size"]:,} bytes • SHA256 {row["sha256"][:16]} • '+row['notes'])

    def add_current_firmware(self):
        if not self.add_to_catalog.get() or not self.image.get(): return
        try:
            path,created=add_file(FIRMWARE,self.image.get())
            self.image.set(str(path));self.refresh_firmware(selected=path)
            self.log(('Added to local firmware folder: ' if created else 'Already in local firmware folder: ')+path.name)
            self.log('Local only. Use GitHub push commands to review and push when ready.')
        except Exception as exc: messagebox.showerror('Cannot add firmware',str(exc),parent=self)

    def open_firmware_folder(self):
        try:
            FIRMWARE.mkdir(parents=True,exist_ok=True)
            if os.name=='nt': os.startfile(str(FIRMWARE))
        except OSError as exc: messagebox.showerror('Firmware folder',str(exc),parent=self)

    def open_github(self):
        commands=('cd /d "'+str(PROJECT)+'"\ngit add firmware\ngit diff --cached --stat\ngit commit -m "Add gadget firmware"\ngit push')
        self.log('GitHub commands (run in Windows Command Prompt from a Git clone):\n'+commands)
        messagebox.showinfo('Push firmware using Command Prompt',
            'Run these commands from your local Git clone:\n\n'+commands+
            '\n\nReview the staged files before committing. Commands are also in the terminal log.\nA downloaded ZIP folder must first be added to a clone. See docs/GITHUB_SETUP.md.',parent=self)

    def refresh(self):
        ports=list(list_ports.comports());self.port_map={f'{p.device} — {p.description}':p.device for p in ports}
        self.ports['values']=list(self.port_map)
        if self.port.get() not in self.port_map: self.port.set(next(iter(self.port_map),''))

    def open_data(self):
        DATA.mkdir(parents=True,exist_ok=True)
        if os.name=='nt': os.startfile(str(DATA))

    def log(self,text): self.events.put(('log',str(text)))
    def stage(self,text,pct): self.events.put(('stage',(text,pct)))
    def ask(self,title,text):
        done=threading.Event();answer=[]
        self.events.put(('ask',(title,text,done,answer)));done.wait()
        if not answer[0]: raise RuntimeError('Cancelled before continuing.')

    def poll(self):
        try:
            while True:
                kind,data=self.events.get_nowait()
                if kind=='log':
                    self.console.configure(state='normal');self.console.insert('end',data+'\n');self.console.see('end');self.console.configure(state='disabled')
                    if self.logfile: self.logfile.write(data+'\n');self.logfile.flush()
                    if 'CONNECT GADGET NOW' in data: self.status.set('CONNECT GADGET NOW — waiting for the gadget…')
                elif kind=='stage': self.status.set(data[0]);self.progress['value']=data[1]
                elif kind=='ask':
                    title,text,done,answer=data;answer.append(messagebox.askokcancel(title,text,parent=self));done.set()
                elif kind=='finish':
                    ok,text=data;self.set_busy(False)
                    if self.logfile: self.logfile.close();self.logfile=None
                    if ok: messagebox.showinfo('Completed',text,parent=self)
                    else: messagebox.showerror('Stopped',text,parent=self)
        except queue.Empty: pass
        self.after(80,self.poll)

    def set_busy(self,value):
        self.busy=value
        for b in self.actions+self.edit_buttons+[self.refresh_button]: b.configure(state='disabled' if value else 'normal')
        self.ports.configure(state='disabled' if value else 'readonly')
        self.catalog.configure(state='disabled' if value else 'readonly')
        self.bin_entry.configure(state='disabled' if value else 'readonly')
        self.stop_button.configure(state='normal' if value else 'disabled')

    def request_stop(self):
        self.stop.set();self.stop_button.configure(state='disabled');self.log('Stop requested. A page already being programmed will finish first.')

    def close_app(self):
        if self.busy: messagebox.showinfo('Operation active','Wait for completion or use Stop after current page.',parent=self)
        else: self.destroy()

    def start(self,mode):
        if self.busy: return
        port=self.port_map.get(self.port.get())
        if not port: messagebox.showerror('Select port','Select the CJP COM port.');return
        avr=Path(self.avr.get())
        conf=avr.parent.parent/'etc/avrdude.conf'
        if not avr.is_file() or not conf.is_file():
            messagebox.showerror('AVRDUDE required','Browse to avrdude.exe from your Arduino installation. Its matching etc/avrdude.conf must exist.');return
        self.remember_avrdude(avr)
        source=None
        try:
            if mode=='upgrade':
                source=Path(self.image.get()).read_bytes();validate_image(source,32768)
                selected=Path(self.image.get()).resolve()
                if selected.parent==FIRMWARE.resolve():
                    row=next((r for r in scan(FIRMWARE) if r['path'].resolve()==selected),None)
                    if not row or row['error'] or row.get('sha256')!=sha(source):
                        raise ValueError('Firmware catalog integrity check failed. Refresh the firmware list.')
            elif mode=='restore':
                p=filedialog.askopenfilename(title='Select this gadget’s backup.json',filetypes=[('CJP backup','backup.json')])
                if not p: return
                source=load_backup(p)
                if not messagebox.askokcancel('Restore selected backup','Use only the backup belonging to this physical gadget.\n\n'+p+'\n\nIts application will be restored; its bootloader will be preserved.'): return
            DATA.mkdir(parents=True,exist_ok=True);(DATA/'logs').mkdir(exist_ok=True)
            self.logfile=(DATA/'logs'/(datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.txt')).open('x',encoding='utf-8')
        except Exception as exc: messagebox.showerror('Cannot start',str(exc));return
        self.stop.clear();self.progress['value']=0;self.set_busy(True)
        threading.Thread(target=self.worker,args=(mode,port,avr,conf,source),daemon=True).start()

    def worker(self,mode,port,avr,conf,source):
        link=None;backup_path=None;writing=False;outcome=None
        try:
            self.log('CodyNick Gadgets Updater v4 — '+mode.upper())
            self.ask('Disconnect gadget','Disconnect the gadget from CJP. Leave CJP connected by USB.\nClose Arduino Serial Monitor and other serial programs.\n\nClick OK to prepare the CJP automatically.')
            if self.stop.is_set(): raise RuntimeError('Stopped before programming.')
            self.stage('Preparing CJP gateway…',2)
            command=[str(avr),'-C',str(conf),'-p','atmega328p','-c','arduino','-P',port,'-b','115200','-D','-U','flash:w:'+str(ASSETS/'gateway_v6.hex')+':i']
            with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)) as proc:
                for line in proc.stdout: self.log(line.rstrip())
                if proc.wait()!=0: raise RuntimeError('CJP gateway upload failed. Check COM port and close other serial applications.')
            if self.stop.is_set(): raise RuntimeError('Stopped before gadget programming.')
            self.stage('Connecting to CJP…',8);link=Link(port,self.log);link.open()
            self.ask('Ready to connect gadget','Keep the gadget DISCONNECTED.\n\nClick OK, then connect the gadget when the status says CONNECT GADGET NOW.')
            size=link.request('H',timeout=30)
            if size not in (b'\x10',b'\x20'): raise RuntimeError('Unsupported gadget flash size.')
            size=size[0]*1024;link.end=BASE+size;self.log(f'Detected main flash: {size} bytes; PID 0444 confirmed.')
            if mode=='upgrade': validate_image(source,size)
            if mode=='restore' and len(source)!=size: raise RuntimeError('Backup/device flash sizes differ.')
            self.stage('Reading and saving backup — each block read twice…',12)
            current=read_flash(link,size,lambda f:self.stage('Reading backup — each block read twice…',12+f*33),twice=True)
            backup_path=save_backup(DATA/'backups',current,port);self.log('BACKUP_SAVED_AND_VERIFIED: '+str(backup_path))
            profile=identify_bootloader(current[:2048],KNOWN_BOOT_SHA)
            self.log('BOOTLOADER_PROFILE: '+(profile or 'Unrecognized — read-only backup permitted'))
            if not profile:self.log(mismatch_summary(current[:2048]))
            if mode=='backup':
                self.stage('Backup complete.',100);outcome=(True,'Backup saved and verified:\n'+str(backup_path));return
            if not profile:
                raise RuntimeError('Bootloader matches neither recognized profile. No gadget erase/write was sent.\nBackup saved: '+str(backup_path)+'\n'+mismatch_summary(current[:2048]))
            target=make_target(current,source) if mode=='upgrade' else source
            if target[:2048]!=current[:2048]: raise RuntimeError('Selected backup bootloader differs. Restore refused.')
            if self.stop.is_set(): raise RuntimeError('Stopped before gadget erase/write.')
            writing=True
            program(link,current,target,self.log,lambda f:self.stage('Programming and verifying application pages…',45+f*49),self.stop.is_set)
            self.stage('Success — full flash verified.',100)
            self.log('SUCCESS. Disconnect gadget from CJP and reconnect to its normal controller to test operation.')
            outcome=(True,'Programming and full-flash verification passed.\nBootloader and data beyond the BIN are preserved.\n\nDisconnect the gadget from CJP and reconnect it to its normal controller.\n\nBackup: '+str(backup_path))
        except Exception as exc:
            self.log('STOPPED: '+str(exc));self.stage('Stopped — see terminal log.',self.progress_value_fallback())
            text=str(exc)
            if writing: text+='\n\nDisconnect the gadget. Click Restore backup and select:\n'+str(backup_path)+'\n\nFollow the connection prompts. If restore fails, stop and retain the log.'
            else: text+='\n\nNo gadget erase/write was started.'
            outcome=(False,text)
        finally:
            try:
                if link: link.close()
            finally:
                if outcome: self.events.put(('finish',outcome))

    def progress_value_fallback(self): return 0

# Profile of the bootloader verified in both supplied gadget backups.
KNOWN_BOOT_SHA = 'bc7dec5d694bba178dd8948b314ad2c66be008a9ba74382d1dc0f0f53fce7e1c'

if __name__=='__main__': App().mainloop()
