# Local firmware collection

This folder sits beside `app/` inside the same GitHub repository. The GUI lists
its `.bin` files. The included `sevensegment_original.bin` is the 12,072-byte
application successfully programmed with CJP v5. It begins at `0x08000800`.

To add another application, tick **Add browsed BIN to local firmware folder**
and browse to the BIN. You can also tick the checkbox after browsing. Importing
copies the file; the original stays where it was. A companion JSON file records
the name, size, SHA256, address and notes. Duplicate contents reuse the existing
entry. Different versions receive different names; nothing is overwritten.

Names for new imports look like `gadget_v2__a1b2c3d4e5f6.bin`. Keep the BIN and its
JSON together when committing. Edit the JSON `name` and `notes` to describe the
gadget, build version and test results; keep its checksum unchanged. Imported
files start with an explicit unverified status. A successful structural check
does not establish hardware compatibility.

Adding is local only. Use **GitHub push commands…** to display the Command Prompt workflow.
Review, commit, then push the files. Technicians receive the
updated collection after pulling the repository. See `../docs/GITHUB_SETUP.md`.

Application files only: do not add full device backups or bootloader images.
