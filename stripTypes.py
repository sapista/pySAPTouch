"""
Defines possible Ardour stirp types
"""
class StripEnum:
    Empty, AudioTrack, MidiTrack, AudioBus, MidiBus, AuxBus, VCA = list(range(7))

    def __init__(self):
        self.ardourtypes = {'AT': self.AudioTrack, 'MT': self.MidiTrack, 'B': self.AudioBus, 'MB': self.MidiBus,
                            'AX': self.AuxBus, 'V': self.VCA}

    def map_ardour_type(self, sardourtype):
        try:
            return self.ardourtypes[sardourtype]
        except KeyError:
            raise KeyError(f"The type '{sardourtype}' is not mapped in StripEnum.")