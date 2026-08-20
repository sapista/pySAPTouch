#!/usr/bin/env python3

"""
Touchscreen & Pointer Rescue Helper

This utility script manages input mapping and cursor recovery for dual-monitor setups under X11.
It is specifically designed for workflows combining a secondary touchscreen with a primary display and a trackball.

Touchscreen Mapping: Automatically locks the touchscreen input device (QDtech MPI1001) to its dedicated display output (HDMI-1) using xinput.

Smart Cursor Rescue: Monitors physical trackball/mouse movement directly via evdev.
If movement is detected while the cursor is on the touchscreen area, it instantly teleports the pointer back to its last active position on the main monitor.

Low Overhead: Operates on a lightweight, event-driven hardware listening loop to ensure zero impact on system performance.
"""

import evdev
from Xlib import display
import time
import subprocess

# --- CONFIGURATION ---
# 1. X coordinate where your touchscreen begins.
# If your main monitor (the DAW) is 1920x1080 and the touchscreen is to its right,
# then any X >= 1920 means the cursor is on the small screen.
BOUNDARY_X = 3440 

# 2. Part of your trackball's name (you can find it by running 'xinput list' or 'lsinput')
TRACKBALL_NAME = "Kensington Expert Mouse"
# ---------------------

def map_touchscreen():
    print("Mapping touchscreen to HDMI-1...")
    try:
        # By passing it as a list, Python handles spaces seamlessly without quoting issues
        subprocess.run(
            ["xinput", "map-to-output", "QDtech MPI1001", "HDMI-1"],
            check=True
        )
        print("Mapping completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"xinput error while attempting to map: {e}")
    except FileNotFoundError:
        print("Error: 'xinput' command not found in the system.")

def main():
    
    map_touchscreen()
    
    RETURN_X = 0
    RETURN_Y = 0

    # Connect to the X11 display server
    d = display.Display()
    root = d.screen().root

    # Automatically search for the trackball among hardware devices
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    trackball = None
    for dev in devices:
        if TRACKBALL_NAME.lower() in dev.name.lower():
            trackball = dev
            break
    
    if not trackball:
        print(f"Error: No hardware device found with the name '{TRACKBALL_NAME}'")
        return

    print(f"Monitoring movement on: {trackball.name}")
    print("Ready. If the cursor crosses the boundary, it will be returned upon moving the ball.")

    # Infinite loop listening to raw hardware (negligible CPU usage)
    try:
        for event in trackball.read_loop():
            # ecodes.EV_REL means Relative Movement (rolling the mouse ball)
            if event.type == evdev.ecodes.EV_REL:
                
                # Ask X11 where the cursor is at this exact moment
                ptr = root.query_pointer()
                
                # If the cursor is inside or beyond the touchscreen...
                if ptr.root_x >= BOUNDARY_X:
                    # Teleport back to the main screen!
                    root.warp_pointer(RETURN_X, RETURN_Y)
                    d.sync()
                    
                    # Small 100ms pause to avoid saturating X11 if you keep rolling the ball
                    time.sleep(0.1)
                else:
                    RETURN_X = ptr.root_x
                    RETURN_Y = ptr.root_y
                    #print(ptr._data)
                    #print(f"X: {RETURN_X},  Y:{RETURN_Y}")
                    
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
