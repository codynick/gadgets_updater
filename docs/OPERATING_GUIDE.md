# Operating and recovery guide

## Normal upgrade

1. Launch `Start_Updater.bat` from the project root.
2. Select the CJP COM port. Refresh the list if needed.
3. Select a listed firmware or browse an application BIN. The checkbox controls
   whether a browsed file is copied into the local collection. The original
   file is never moved. Local additions work offline.
4. Check that the firmware belongs to the physical gadget being connected.
5. Click **Upgrade gadget**. Disconnect the gadget when instructed. Leave CJP
   connected by USB and close any other serial application.
6. The updater prepares the CJP automatically using the tested v5 gateway.
7. Keep the gadget disconnected through the next dialog. Click OK, then
   connect it only when the status says **CONNECT GADGET NOW**.
8. Wait for backup, programming and full-flash verification to finish. The
   terminal shows the progress and saved backup path.
9. On success, disconnect from CJP and reconnect to the normal controller to
   test the gadget's actual operation.

The local firmware list is not automatic gadget identification. The device PID
and bootloader can be identical across different gadget types. Choose the
correct application. The old Matrix BIN linked at `0x08000000` is unsuitable;
this updater expects an application intended for `0x08000800`.

## Backup and restore

**Backup only** prepares CJP and reads the gadget without gadget erase/write.
Each 64-byte flash block is read twice. Backups contain `original.bin` plus an
integrity-checked `backup.json`. Keep both files together and label the folder
with the physical gadget identity. **Open backups and logs** opens the local
storage directory. GUI v1 and v2 backups use the same format.

If programming fails, disconnect the gadget and click **Restore backup…**.
Select the `backup.json` shown in the failed operation's log/error message.
Confirm that it belongs to this physical gadget. Follow the same guided CJP
preparation and connection sequence. A fresh backup of the current state is
saved before recovery writes. Restore uses the selected original application,
not the currently selected firmware-list item. If restoration fails, stop and
retain the complete log for diagnosis.

**Stop after current page** allows the active page's erase/write/readback to
finish, then stops before another page is programmed. Treat an interrupted
upgrade as incomplete and restore before using the gadget. Keep power connected
while a page is being programmed. Setup/read operations may finish before a
pending stop is acted on.

The tool never erases/writes the first 2 KB bootloader area. Its backup covers
main flash only; no option-byte, protection or mass-erase operation is used.
Restoration depends on the preserved bootloader, working communication and
stable power. A selected BIN must also be compatible with any preserved data
beyond its end. Verification establishes flash contents, not runtime behavior.

## Publish firmware

Adding a file to `firmware/` does not program a gadget and does not send the
file online. After checking its metadata, use **GitHub / Publish…** and follow
the GitHub Desktop review, commit and push instructions. See
[GITHUB_SETUP.md](GITHUB_SETUP.md) for the first-time setup. This version's
GitHub button is a Desktop handoff, not an embedded Git client.

## Standalone Windows EXE

`Build_Windows_EXE.bat` builds an EXE in the project root, beside `firmware/`
and `docs/`. Launch it from there to use the same catalog as the Python GUI.
The EXE bundles Python but still needs AVRDUDE and its matching configuration.
This build requires internet access to install PyInstaller and dependencies;
its Windows output has not yet been built/tested in this environment. Confirm
the new catalog GUI works on the tested computer before distributing builds.
