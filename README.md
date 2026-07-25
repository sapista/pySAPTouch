# OSC Controller for Ardour
Based on a Raspberry Pi with a touch screen and a custom AVR Atmega 2560 board controlling 8 motorized faders.

## UDP Buffer Limits
The UDP buffer is may be limited by the Linux kernel
To make the UDP buffer limit settings permanent so it survives a reboot, add the line:

```text
net.core.rmem_max=4194304
``` 

to the bottom of the /etc/sysctl.conf file.