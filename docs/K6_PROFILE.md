# Additional STM32F030K6 bootloader profile

The previous GUI accepted only the complete 2 KB SHA256 from the original
backed-up gadget. The error 'Bootloader differs from the verified gadget
profile' occurred after device communication and flash reads, before any
application erase/write. It was a profile restriction, not an image-upload
error or proof of an incompatible chip.

The supplied K6 Intel HEX has valid checksums and defines 1312 contiguous bytes
at 0x08000000 through 0x0800051F. It is identical to the earlier supplied
bootloader HEX. Compared with the original device backup, 12 defined bytes
differ. Its application vector-table address remains 0x08000800.

This release adds an exact comparison against every byte defined in that HEX.
The HEX does not define 0x08000520 through 0x080007FF; no value is inferred for
that unused portion of the profile. The whole first 2 KB is backed up, kept
unchanged in the target and verified after programming. It is never erased or
written. Explicit HEX bytes, including the last four zero bytes, must match.
The original complete-2-KB hash profile remains supported.

The HEX is a reference only; the updater DOES NOT install or modify the gadget
bootloader. It retains actual flash-size detection (16/32 KB) and capacity
checks. It does not bypass identification or allow an oversized application.
A matching bootloader does not identify the gadget function or prove that a
selected application BIN is compatible with it.

Backup only now works with an unrecognized bootloader, provided gateway
identification/read access succeeds. The full flash is read twice and saved
before profile checking. Upgrade and Restore still refuse unknown profiles,
logging differences versus the supplied HEX. If the installed image differs
from the reference, send the session log and new backup for comparison; do not
replace the bootloader to make it match.

First hardware test: use Backup only with the K6 gadget. Look for:
BOOTLOADER_PROFILE: Supplied STM32F030K6 bootloader ...
If instead it says Unrecognized, send the saved log and backup. A compiled
Windows EXE must be rebuilt to include this patch; Start_Updater.bat uses the
patched Python source immediately.

31 automated tests passed, including a 32 KB simulated K6 upgrade, preservation
of the complete 2 KB, rejection of changed reference bytes, read-only unknown
backups and refusal to program an unknown bootloader. No K6 hardware upgrade
has yet been tested with this release.
