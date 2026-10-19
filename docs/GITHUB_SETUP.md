# Command-line GitHub workflow

The online repository is https://github.com/codynick/gadgets_updater.
Use Windows Command Prompt. No GitHub Desktop is needed.

## Existing local clone

If `D:\GitHub\gadgets_updater` is already your clone, close the updater and save
any local changes in Git before updating it. Extract this complete archive into
a separate folder and test it there first. This leaves the current clone intact.
When ready, copy the complete release's contents into your clone, retaining its
`.git` folder and your additional `firmware/` entries. Review the differences:

```bat
cd /d "D:\GitHub\gadgets_updater"
git status --short
git diff
```

This release includes its own `.gitignore` and no Git metadata or hardware
backups. Do not delete your clone or its firmware to install it.

## First clone, if needed

Check `git --version`. If Git is not installed, install Git for Windows and
reopen Command Prompt. Then:

```bat
if not exist "D:\GitHub" mkdir "D:\GitHub"
cd /d "D:\GitHub"
git clone https://github.com/codynick/gadgets_updater.git
```

Copy the contents of the extracted release's `gadgets_updater` folder into
`D:\GitHub\gadgets_updater`, replacing the prepared project files as appropriate.
`Start_Updater.bat`, `app`, `firmware` and `docs` must sit directly in the clone.
Avoid a second nested `gadgets_updater` folder.

After reviewing, commit and push:

```bat
cd /d "D:\GitHub\gadgets_updater"
git add .
git diff --cached --stat
git commit -m "Update complete gadget updater with K6 profile and status LED"
git push -u origin HEAD
```

If Git requests commit identity, set your own name and commit email locally:

```bat
git config user.name "YOUR NAME"
git config user.email "YOUR GITHUB COMMIT EMAIL"
```

Repeat the commit and push after setting those values. Complete GitHub
sign-in if prompted. Stop and inspect any rejected push; no force push is needed
for this workflow.

## Subsequent BIN additions

In the GUI, tick **Add browsed BIN to local firmware folder**, then browse to
an application BIN. The BIN is copied and checksum metadata is created. The
original file is retained. You can also tick the checkbox after browsing.
Duplicate contents reuse an existing entry; different contents get a new name.
Imported firmware starts as unverified; a copied or pushed file is not proof of
hardware compatibility.

To publish new BINs from a clone:

```bat
cd /d "D:\GitHub\gadgets_updater"
git add firmware
git diff --cached --stat
git commit -m "Add gadget firmware"
git push
```

The GUI's **GitHub push commands…** button displays these commands, adjusted
for its own project folder. It does not run them or upload anything.

## Receive updates on another PC

Clone the repository once. Later, from a clean local working tree, run:

```bat
git pull --ff-only
```

If that stops because local changes or divergent commits exist, retain the
files and resolve the situation; do not discard unshared BINs. Each clone has
its own local firmware collection; push/pull share the committed files.
A ZIP download can run the updater but is not itself a Git clone.

## Hardware backups

Hardware backups/logs remain under `%LOCALAPPDATA%\CJP Upgrader`, outside the
repository. Git history is separate from gadget restoration. Retain each
physical gadget's backup folder with both `original.bin` and `backup.json`.
