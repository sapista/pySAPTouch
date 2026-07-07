"""
This class seats in between the maingui and the pyFaderSerialCOM enabling an abstraction layer of the fader bank concept.
All serial communciations with the AVR are managed from within this class.
This class keeps track of faders during edit/standard operation modes
"""
from gi.repository import GObject
import pyFaderSerialCOM
from enum import Enum

class FaderBankState(Enum):
    EIGHT_CHANNELS_FADERS = 1
    SINGLE_CHANNEL_EDIT = 2

class BankAvrController(GObject.GObject):

    __gsignals__ = {
        'encoder_increment': (GObject.SIGNAL_RUN_FIRST, None,
                                    (float, )),  #  value

        'fader_bank_mode_changed': (GObject.SIGNAL_RUN_FIRST, None,
                             (int, float)),  # channel, value

        'fader_bank_mode_untouched': (GObject.SIGNAL_RUN_FIRST, None,
                                (int,)),  # value

        'trim_single_mode_changed': (GObject.SIGNAL_RUN_FIRST, None,
                                     (float,)),  # value

        'trim_single_mode_untouched': (GObject.SIGNAL_RUN_FIRST, None, ()),

        'fader_single_mode_changed': (GObject.SIGNAL_RUN_FIRST, None,
                                (float,)),  # value

        'fader_single_mode_untouched': (GObject.SIGNAL_RUN_FIRST, None, ()),


        'pan_pos_single_mode_changed': (GObject.SIGNAL_RUN_FIRST, None,
                                      (float,)),  # value

        'pan_pos_single_mode_untouched': (GObject.SIGNAL_RUN_FIRST, None, ()),

        'pan_width_single_mode_changed': (GObject.SIGNAL_RUN_FIRST, None,
                                      (float,)),  # value

        'pan_width_single_mode_untouched': (GObject.SIGNAL_RUN_FIRST, None, ()),

        'send_single_mode_changed': (GObject.SIGNAL_RUN_FIRST, None,
                                      (int, float,)),  # channel, value

        'send_single_mode_untouched': (GObject.SIGNAL_RUN_FIRST, None,
                                       (int,)) # channel, warning! it is not a byte made of bits like in fader_bank_mode_untouched. It is the untouched send channel

    }

    def __init__(self, port, baudrate, fader_min, fader_max):
        GObject.GObject.__init__(self)

        self.state = FaderBankState(1)
        self.faders_pos = [0.0] * 8 #Store positions of eight faders in the bank
        self.trim_edit_pos = 0.0 #Store positions of a single trim control in edit mode
        self.fader_edit_pos = 0.0  # Store positions of a single fader in edit mode
        self.pan_edit_pos = 0.0  # Store positions of a single pan position in edit mode
        self.pan_edit_width = 0.0  # Store positions of a single pan width in edit mode
        self.sends_pos = [0.0] * 4 #Store positions of four sends in the bank

        self.avrCOM = pyFaderSerialCOM.FaderCOM(port, baudrate, fader_min, fader_max)
        self.avrCOM.connect("fader_changed", self.on_fader_moved)
        self.avrCOM.connect("fader_untouched", self.on_fader_untouched)
        self.avrCOM.connect("encoder_changed", self.on_encoder_changed)

    def on_encoder_changed(self, event, value):
        self.emit('encoder_increment', value)

    def on_fader_moved(self, event, channel, value):
        if self.state == FaderBankState.EIGHT_CHANNELS_FADERS:
            self.faders_pos[channel] = value
            self.emit('fader_bank_mode_changed', channel, value)
        elif self.state == FaderBankState.SINGLE_CHANNEL_EDIT:
            if channel == 0:
                self.trim_edit_pos = value * 40.0 - 20.0 #convert from 0 to 1 range to -20 to 20 dB range
                self.emit('trim_single_mode_changed', self.trim_edit_pos)
            elif channel == 1:
                self.fader_edit_pos = value
                self.emit('fader_single_mode_changed', value)
            elif channel == 2:
                self.pan_edit_pos = value
                self.emit('pan_pos_single_mode_changed', value)
            elif channel == 3:
                self.pan_edit_width = value
                self.emit('pan_width_single_mode_changed', value)
            else:
                self.sends_pos[channel - 4] = value
                self.emit('send_single_mode_changed', channel - 4,  value)

        return True

    def on_fader_untouched(self, event, value):
        if self.state == FaderBankState.EIGHT_CHANNELS_FADERS:
            self.emit('fader_bank_mode_untouched', value)
        elif self.state == FaderBankState.SINGLE_CHANNEL_EDIT:
            if value & 0b00000001 == 0b00000001:
                self.emit('trim_single_mode_untouched')
            elif value & 0b00000010 == 0b00000010:
                self.emit('fader_single_mode_untouched')
            elif value & 0b00000100 == 0b00000100:
                self.emit('pan_pos_single_mode_untouched')
            elif value & 0b00001000 == 0b00001000:
                self.emit('pan_width_single_mode_untouched')
            else:
                for i in range(0, 4):
                    if value >> (4 + i) == 1:
                        self.emit('send_single_mode_untouched', i)

        return True

    def set_state(self, state):
        self.state = state
        if state == FaderBankState.EIGHT_CHANNELS_FADERS:
            for i in range(0,8):
                self.avrCOM.moveFader(i, self.faders_pos[i])

        elif state == FaderBankState.SINGLE_CHANNEL_EDIT:
            self.avrCOM.moveFader(0, 0.025 * self.trim_edit_pos  + 0.5) #Converting it from -20 to 20 dB range to 0 to 1
            self.avrCOM.moveFader(1, self.fader_edit_pos)
            self.avrCOM.moveFader(2, self.pan_edit_pos)
            self.avrCOM.moveFader(3, self.pan_edit_width)
            for i in range(0,4):
                self.avrCOM.moveFader(i+4, self.sends_pos[i])

        #send untouch events for all faders before changing state!
        self.emit('fader_bank_mode_untouched', 0xFF)
        self.emit('trim_single_mode_untouched')
        self.emit('fader_single_mode_untouched')
        self.emit('pan_pos_single_mode_untouched')
        self.emit('pan_width_single_mode_untouched')
        for i in range(0, 4):
            self.emit('send_single_mode_untouched', i) #TODO this is throwing errors


    def get_state(self):
        return self.state

    def move_bank_fader(self, iFader, value):
        if self.faders_pos[iFader] != value:
            self.faders_pos[iFader] = value
            if self.state == FaderBankState.EIGHT_CHANNELS_FADERS:
                self.avrCOM.moveFader(iFader, value)

    def move_single_trim(self, value):
        if self.trim_edit_pos != value:
            self.trim_edit_pos = value
            if self.state == FaderBankState.SINGLE_CHANNEL_EDIT:
                self.avrCOM.moveFader(0, 0.025 * value + 0.5) #Converting it from -20 to 20 dB range to 0 to 1

    def move_single_fader(self, value):
        if self.fader_edit_pos != value:
            self.fader_edit_pos = value
            if self.state == FaderBankState.SINGLE_CHANNEL_EDIT:
                self.avrCOM.moveFader(1, value)

    def move_single_pan_pos(self, value):
        if self.pan_edit_pos != value:
            self.pan_edit_pos = value
            if self.state == FaderBankState.SINGLE_CHANNEL_EDIT:
                self.avrCOM.moveFader(2, value)

    def move_single_pan_width(self, value):
        if self.pan_edit_width != value:
            self.pan_edit_width = value
            if self.state == FaderBankState.SINGLE_CHANNEL_EDIT:
                self.avrCOM.moveFader(3, value)

    def move_single_send(self, iSend, value):
        if self.sends_pos[iSend] != value:
            self.sends_pos[iSend] = value
            if self.state == FaderBankState.SINGLE_CHANNEL_EDIT:
                self.avrCOM.moveFader(4+iSend, value)

    def close(self):
        self.avrCOM.close()
