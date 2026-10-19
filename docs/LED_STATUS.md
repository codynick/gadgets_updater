# CJP connection LED — gateway v6

The first RGB pixel changes from blue to green after the complete gadget
handshake, INIT ACK, command identification, product ID and flash-size checks
succeed. Blue means idle/waiting or a connection/serial-operation failure.
Other RGB pixels are cleared. Green indicates a verified programming connection;
it does not mean firmware programming or runtime testing has completed.

The gateway does not continuously monitor unplugging. An unplugged gadget can
leave the light green until a serial operation fails or CJP resets. Starting a
new session resets the status to blue. No LED update runs while a gadget UART
reply is in progress. The PC protocol remains CJP5 for host compatibility.

Original Lite's compiled configuration identifies 16 GRB/800 kHz pixels on A2.
The new routine uses the same 20 CPU-cycle bit waveform at 16 MHz and a 300 us
latch interval. Brightness is 10/255. Status updates preserve the A4/A5 port bits.
The first pixel itself changes color; this does not reproduce Lite's separate
blue and green pixel arrangement.

Verification: AVR compilation with warnings as errors; compiled blue and green
waveforms decoded and checked for all 384 bits, exact 20-cycle periods and
unchanged A4/A5 values; all 22 host tests pass. Physical LED behavior still needs
its first test. Gadget flash/bootloader guards and serial protocol are unchanged.

To test without writing the gadget, launch Start_Updater.bat and use Backup only.
The app automatically uploads gateway_v6.hex to CJP, then prompts connection.
The light should be blue after setup and green when identification succeeds.
Backups/logs remain outside the Git repository.
