"""
Defines possible Ardour stirp types
"""
class StripEnum:
    Empty, Track, MidiTrack, Bus, MidiBus, AuxBus, VCA = list(range(7))
