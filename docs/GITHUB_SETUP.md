# Create CodyNick_Gadgets_Updater on GitHub

This package is prepared locally. An online GitHub repository has **not** been
created by the package. The following steps create it under your own account.
Use one repository containing both `app/` and `firmware/`; a second repository
or Git submodule is unnecessary here.

## 1. Install and sign in

Install [GitHub Desktop](https://desktop.github.com/) and sign into your GitHub
account through its browser sign-in flow. Return to Desktop after authentication.
You do not need to place a GitHub password or token in the updater.

## 2. Create the local repository

In Desktop, choose **File → New repository**. Enter:

| Field | Value |
| --- | --- |
| Name | `CodyNick_Gadgets_Updater` |
| Description | `Technician GUI and firmware collection for CodyNick gadgets` |
| Local path | `D:\GitHub` (or another writable parent folder) |
| Initialize with README | Checked |
| Git ignore | None — the prepared project includes its own |
| License | None for now |

Click **Create repository**. With those values, the actual project folder is
`D:\GitHub\CodyNick_Gadgets_Updater`. The Local path field is its **parent**.

## 3. Copy the prepared files

Extract the downloaded ZIP into a temporary folder, such as Downloads. Open
the extracted `CodyNick_Gadgets_Updater` folder. Copy **its contents** into the
newly created local repository. Replace the automatically created README with
the provided README when asked. Keep the `.git` folder created by Desktop.

The destination should contain `Start_Updater.bat`, `README.md`, `.gitignore`,
`app/`, `firmware/` and `docs/` directly. Avoid a second nested folder named
`CodyNick_Gadgets_Updater` inside the repository. Windows may hide file extensions;
compare the names carefully.

Double-click `Start_Updater.bat` from this destination folder. The firmware list
should contain **Seven-segment — original firmware**. Verify the list and Browse
controls first; adding files does not program hardware.

## 4. Commit and publish

Return to Desktop and select this repository. Review the Changes list. Enter
the summary `Add CodyNick updater and initial seven-segment firmware`, then
click **Commit to main** (or the branch name shown).

Click **Publish repository**. Keep **Keep this code private** checked for the
initial project, select your personal account or the intended organization,
and publish. Then use **Repository → View on GitHub** to check it online.

Its address will be `https://github.com/YOUR_ACCOUNT/CodyNick_Gadgets_Updater`.
The folder name alone does not create that address; publishing does.

## 5. Add a BIN and share it later

In the updater, tick **Add browsed BIN to local firmware folder** and browse to
the application BIN. The GUI copies it and creates a JSON metadata file. It
also switches the selected path to the saved copy. You can tick the checkbox
after browsing to add the current file. Identical contents reuse an existing
entry. Different contents always receive a new filename.

Click **GitHub / Publish…**. This opens publishing instructions and attempts to
launch the standard GitHub Desktop installation. It does not upload anything.
In Desktop, select **CodyNick_Gadgets_Updater**, review the new `firmware/*.bin`
and `.json` pair, enter a summary such as `Add seven-segment v2 firmware`, commit,
then click **Push origin**. The files are now shared with people who have access.
You can continue using local firmware when offline and push later.

The metadata `name` and `notes` may be edited to identify a gadget/version and
record test results. Do not change the checksum without replacing the BIN.
New imports are marked unverified; adding or pushing one does not prove it works.

## 6. Give technicians the collection

For a private repository, grant the intended people access through GitHub's
repository access settings. Technicians can clone it through GitHub Desktop
and run `Start_Updater.bat`. Each clone contains the updater and firmware folder.
On subsequent visits, use **Fetch origin**, then **Pull origin** if offered,
before opening the updater. Resolve or commit local changes before pulling;
do not discard firmware that has not been shared yet.

For technicians who should only program gadgets, distribute a tested EXE with
its sibling firmware folder and the required AVRDUDE tool/configuration, or a
project ZIP. A downloaded ZIP is not a Git checkout: it cannot itself push or
pull changes. Use a clone for maintainers who will contribute BIN files.

## Local vs. GitHub vs. gadget

| Action | Result |
| --- | --- |
| Browse, checkbox off | Select external BIN only |
| Browse, checkbox on | Copy BIN and metadata into the local firmware folder |
| Commit | Save selected project changes in local Git history |
| Push | Upload committed changes to GitHub |
| Pull | Receive committed changes from GitHub |
| Upgrade gadget | Program the connected gadget after creating its backup |
| Restore backup | Restore that physical gadget's saved application |

Git history and gadget recovery are separate. Keep the verified hardware
backups. They are saved outside the repository at `%LOCALAPPDATA%\CJP Upgrader`.
The supplied `.gitignore` excludes caches, builds and common backup/log paths.
The initial project contains an application BIN, not full device backups.

## Official references

- [Install and authenticate GitHub Desktop](https://docs.github.com/en/desktop/installing-and-authenticating-to-github-desktop)
- [Create and publish a repository](https://docs.github.com/en/desktop/overview/creating-your-first-repository-using-github-desktop)
- [Review, commit and push changes](https://docs.github.com/en/desktop/making-changes-in-a-branch/committing-and-reviewing-changes-to-your-project-in-github-desktop)
- [Clone a repository](https://docs.github.com/en/desktop/adding-and-cloning-repositories/cloning-a-repository-from-github-to-github-desktop)
