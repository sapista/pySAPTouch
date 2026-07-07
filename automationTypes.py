"""
This files defines the available Ardour automation modes in a unified Enum
"""
from enum import IntEnum

class AutomationModes(IntEnum):
    NOT_SET = -1
    MANUAL = 0
    PLAY = 1
    WRITE = 2
    TOUCH = 3
    LATCH = 4