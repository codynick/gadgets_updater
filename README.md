# CodyNick_Gadgets_Updater

Windows technician GUI for updating compatible CodyNick STM32 gadgets through
an Arduino Uno CJP. Includes COM-port selection, a local firmware list, BIN
browsing, live operation logs, progress, automatic backup and recovery.

## Start

1. Keep this project in a writable folder.
2. Double-click **Start_Updater.bat**.
3. Choose the CJP port (COM6 on the tested machine).
4. Choose **Seven-segment — original firmware** from **Local firmware**, or
   browse an application BIN.
5. Click **Upgrade gadget** and follow the connection prompts. The app handles
   CJP preparation, backup, programming and verification.

Python, tkinter and pyserial are required. The tested computer already has them.
For another computer, install Python and run `py -m pip install -r requirements.txt`.
AVRDUDE is discovered in Arduino15's Arduino/MiniCore packages, or can be browsed
manually together with its matching `../etc/avrdude.conf`.

## Files

| Path | Purpose |
| --- | --- |
| `app/` | GUI, programming engine, tested CJP v5 gateway and tests |
| `firmware/` | Application BIN collection and per-file metadata |
| `Start_Updater.bat` | Launch the GUI |
| `Build_Windows_EXE.bat` | Optional local Windows EXE build |
| `docs/GITHUB_SETUP.md` | Repository creation, publishing and daily use |
| `docs/OPERATING_GUIDE.md` | Firmware import, update and recovery instructions |

## Add firmware

Tick **Add browsed BIN to local firmware folder**, then browse a BIN. It is
copied into `firmware/`, appears in the list, and gets checksum metadata. No
network connection is needed. Exact duplicates are reused; existing versions
are never replaced. Untick the checkbox to use an external BIN without adding it.

**GitHub / Publish…** opens guidance and GitHub Desktop if installed. It does
not commit or push automatically. In Desktop, select this project, review the
BIN and JSON changes, commit, then push. See the setup guide for first use.

## Programming behavior

Supported devices report PID `0444`, 16 or 32 KB flash, and the exact bootloader
profile verified in the original gadget backups. Binaries must be application
images intended for `0x08000800`. The tool checks size, initial stack and reset
vector; those checks cannot prove correct linking, interrupt remapping, gadget
type or runtime behavior. Selecting the correct gadget firmware remains essential.

The complete BIN is written at `0x08000800`. No first-2-KB skipping occurs inside
the BIN. Device flash pages 0 and 1 are excluded by host and gateway firmware.
Before writing, each flash block is read twice and a verified main-flash backup
is saved. The application is erased and written page by page, preserving all
bytes after the BIN from the current backup. Each page and then the entire
flash are verified. Preserved trailing data must suit the new application.

Backups and logs stay in `%LOCALAPPDATA%\CJP Upgrader`, outside this project.
**Restore backup…** accepts the original GUI v1 backups as well as new ones.
Keep each backup's `original.bin` and `backup.json` together. Main-flash backups
do not include option bytes. Recovery relies on the preserved bootloader and
working power/communication. Full details are in the operating guide.

## Build and verification

`Run_Tests.bat` runs the simulated flash, workflow and firmware catalog tests.
All 22 automated tests passed during preparation, including duplicate imports,
version preservation, checksum tampering, backup-before-write and recovery.
The original CJP v5 programming workflow was successfully tested on the
seven-segment gadget. This version adds the catalog and GitHub Desktop handoff;
the new GUI controls still need their first Windows test.

`Build_Windows_EXE.bat` builds the executable in the project root, beside
`firmware/`. Python is not needed on a computer running that EXE; AVRDUDE and
its matching configuration remain required. The compiled EXE is ignored by Git.
Its Windows build has not been executed in this development environment.

No open-source license is selected in this starter; choose the project's
licensing policy before publishing it publicly.
