"""
A widget conntaining multiple stripselwidgets in a Gtk.Grid
"""

from gi.repository import Gtk, GObject, GLib
from pandas.core.computation import check

import stripTypes
from stripselwidget import StripSelWidget
from stripTypes import StripEnum

class StripTable(Gtk.Grid):
    __gsignals__ = {
        'bank_channel_fader_changed': (GObject.SIGNAL_RUN_LAST, None,
                                      (int, float)),

        'bank_channel_fader_gain_changed': (GObject.SIGNAL_RUN_LAST, None,
                                       (int, float)),

        'bank_channel_solo_changed': (GObject.SIGNAL_RUN_LAST, None,
                               (int, bool)),

        'bank_channel_mute_changed': (GObject.SIGNAL_RUN_LAST, None,
                                      (int, bool)),

        'bank_channel_rec_changed': (GObject.SIGNAL_RUN_LAST, None,
                                      (int, bool)),

        'bank_channel_select_changed': (GObject.SIGNAL_RUN_LAST, None,
                                     (int, bool)),

        'bank_channel_ssid_name_changed': (GObject.SIGNAL_RUN_LAST, None,
                                        (int, int, str)),

        'bank_channel_type_changed': (GObject.SIGNAL_RUN_LAST, None,
                                        (int, int)),

        'strip_select_changed': (GObject.SIGNAL_RUN_LAST, None,
                                 (int,))
    }

    def __init__(self, bank_size, max_strips = 24, meter_pixels_x_seconds = None, is_send = False):
        super(StripTable, self).__init__()

        self.strips_list_widgets = [] #Stores the list of select widgets
        self.bank_size = bank_size
        self.current_selected_strip_widget_idx = None
        self.current_selected_bank_idx = None
        self.send_mode = is_send
        self.vca_mode = False

        #self.viewport_table = Gtk.Viewport()
        #self.table = Gtk.Grid()
        self.set_row_spacing(5)
        self.set_column_homogeneous(True)
        #self.viewport_table.add(self.table)
        #self.add(self.viewport_table) #TODO remove viewports, no scroll anymore!
        #self.add(self.table)

        #self.table = Gtk.Label(label="Strip list is empty, click the refresh button to start DAW comunication")  #TODO remove?
        #self.viewport_table = Gtk.Viewport()
        #self.viewport_table.add(self.table) #TODO remove?
        #self.add(self.viewport_table)

        #self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC) #TODO remove

        #Add strip widgets
        for i in range(0, max_strips):
            self._append_strip()
        self._fill_strips()

        # Meters, global refresh timer
        if meter_pixels_x_seconds is not None:
            self.timeout_meter_interval = round(1000.0 / meter_pixels_x_seconds)  # Timeout interval in milliseconds
            GLib.timeout_add(self.timeout_meter_interval, self.on_meter_refresh_timeout)

    def get_number_of_strips(self):
        return len(self.strips_list_widgets)

    def get_current_selected_strip_index(self):
        return self.current_selected_strip_widget_idx

    def get_current_selected_strip_ssid(self):
        if (self.current_selected_strip_widget_idx is None):
            return None
        return self.strips_list_widgets[self.current_selected_strip_widget_idx].get_ssid()

    def get_strip_ssid(self, index):
        return self.strips_list_widgets[index].get_ssid()

    def _append_strip(self):
        if self.send_mode:
            self.strips_list_widgets.append(StripSelWidget(len(self.strips_list_widgets),
                                                           len(self.strips_list_widgets) + 1,
                                                           len(self.strips_list_widgets) // self.bank_size,
                                                           len(self.strips_list_widgets) % self.bank_size,
                                                           True))
        else:
            self.strips_list_widgets.append(StripSelWidget(len(self.strips_list_widgets),
                                                                      len(self.strips_list_widgets) + 1,
                                                                      len(self.strips_list_widgets) // self.bank_size,
                                                                      len(self.strips_list_widgets) % self.bank_size,
                                                                      False))

    def clear_strips(self):
        self.current_selected_strip_widget_idx = None
        self.current_selected_bank_idx = None

        #Clear strips
        for i in range(0,  len(self.strips_list_widgets)):
            self.strips_list_widgets[i].set_type(StripEnum.Empty)
            self.strips_list_widgets[i].set_name("")
            self.strips_list_widgets[i].set_solo(False)
            self.strips_list_widgets[i].set_mute(False)
            self.strips_list_widgets[i].set_rec(False)
            self.strips_list_widgets[i].set_inputs_outputs(0,0)
            self.strips_list_widgets[i].hide_strip()

        #Clear banks
        for i in range(0, self.bank_size):
            self.emit('bank_channel_ssid_name_changed',
                      i,
                      0,
                      " ")

            self.emit('bank_channel_type_changed',
                      i,
                      StripEnum.Empty)

            self.emit('bank_channel_mute_changed',
                      i,
                      False)

            if not self.send_mode:
                # In send mode we do not send solo and rec
                self.emit('bank_channel_solo_changed',
                          i,
                          False)

                self.emit('bank_channel_rec_changed',
                           i,
                           False)

            self.emit('bank_channel_fader_changed',
                      i,
                      0.0)

            self.emit('bank_channel_fader_gain_changed',
                      i,
                      -100.0)

            self.emit('bank_channel_select_changed',
                      i,
                      False)

    def _fill_strips(self):
        for i in range(0, len(self.strips_list_widgets)):
            self.attach(self.strips_list_widgets[i],
                              i - self.bank_size * self.strips_list_widgets[i].get_bank(),
                              self.strips_list_widgets[i].get_bank(),
                              1,
                              1)
            self.strips_list_widgets[i].connect("strip_selected", self.on_strip_selected)
            self.strips_list_widgets[i].hide_strip()
            self.strips_list_widgets[i].set_sensitive(False)

        if len(self.strips_list_widgets) < self.bank_size:
            # Insert empty columns to fill at least self.bank_size columns, use and empty label to achieve that
            for i in range(len(self.strips_list_widgets), self.bank_size):
                self.attach(Gtk.Label(), i, 0, 1, 1)

    def get_strip_name(self,ssid):
        if self.check_if_ssid_exists(ssid):
            return  self.strips_list_widgets[ssid - 1].get_name()
        else:
            return None

    def set_strip_name(self, ssid, name):
        #print("set_strip_name on ssid '%d' with value '%s'" % (ssid, name))
        if self.current_selected_bank_idx == self.strips_list_widgets[ssid - 1].get_bank():
            self.emit('bank_channel_type_changed',
                      self.strips_list_widgets[ssid - 1].get_bank_index(),
                      self.strips_list_widgets[ssid - 1].get_type())

        #Avoid empty names, Ardour return empty strips as " "
        if len(name) == 0 or name == " ":
            return

        if self.check_if_ssid_exists(ssid):
            self.strips_list_widgets[ssid-1].set_name(name)
            if self.send_mode:
                self.strips_list_widgets[ssid - 1].set_type(StripEnum.AuxBus) #Its a send
            else :
                self.strips_list_widgets[ssid - 1].set_type(StripEnum.VCA) #Start assuming its a VCA
            if self.current_selected_bank_idx == self.strips_list_widgets[ssid - 1].get_bank():
                self.emit('bank_channel_ssid_name_changed', self.strips_list_widgets[ssid - 1].get_bank_index(), ssid, name)

            #In VCA mode force to select the whole first bank
            if self.vca_mode and ssid == 1:
                self.strip_select(ssid, True, as_VCA=True)

    def set_vca_mode(self, bVcaMode):
        self.vca_mode = bVcaMode

    def set_fader(self, ssid, value):
        if self.check_if_ssid_exists(ssid):
            self.strips_list_widgets[ssid - 1].set_fader(value)  # Store fader, used in send mode
            bank_num = self.strips_list_widgets[ssid - 1].get_bank()
            if self.current_selected_bank_idx == bank_num:
                self.emit('bank_channel_fader_changed', self.strips_list_widgets[ssid - 1].get_bank_index(), value)

    def set_fader_gain(self, ssid, value):
        if self.check_if_ssid_exists(ssid):
            self.strips_list_widgets[ssid - 1].set_fader_gain(value)  # Store fader gain, used in send mode
            bank_num = self.strips_list_widgets[ssid - 1].get_bank()
            if self.current_selected_bank_idx == bank_num:
                self.emit('bank_channel_fader_gain_changed', self.strips_list_widgets[ssid - 1].get_bank_index(), value)

    def set_solo(self, ssid, value):
        if  self.check_if_ssid_exists(ssid):
            self.strips_list_widgets[ssid - 1].set_solo(value)
            if self.current_selected_bank_idx == self.strips_list_widgets[ssid - 1].get_bank():
                self.emit('bank_channel_solo_changed', self.strips_list_widgets[ssid - 1].get_bank_index(), value)

    def set_mute(self, ssid, value):
        if  self.check_if_ssid_exists(ssid):
            self.strips_list_widgets[ssid - 1].set_mute(value)
            if self.current_selected_bank_idx == self.strips_list_widgets[ssid - 1].get_bank():
                self.emit('bank_channel_mute_changed', self.strips_list_widgets[ssid - 1].get_bank_index(), value)

    def set_rec(self, ssid, value):
        if  self.check_if_ssid_exists(ssid):

            # If it has rec button so it must be an audio/midi track
            if ((self.strips_list_widgets[ssid - 1].get_type() is not StripEnum.Empty) and
                    (self.strips_list_widgets[ssid - 1].get_type() is not StripEnum.Track)):

                self.strips_list_widgets[ssid - 1].set_type(StripEnum.Track)
                if self.current_selected_bank_idx == self.strips_list_widgets[ssid - 1].get_bank():
                    self.emit('bank_channel_type_changed',
                        self.strips_list_widgets[ssid - 1].get_bank_index(),
                        self.strips_list_widgets[ssid - 1].get_type())

            #Set REC value
            self.strips_list_widgets[ssid - 1].set_rec(value)
            if self.current_selected_bank_idx == self.strips_list_widgets[ssid - 1].get_bank():
                self.emit('bank_channel_rec_changed', self.strips_list_widgets[ssid - 1].get_bank_index(), value)

    def has_panner(self, ssid):
        #print(f"SSID '{ssid}' has panner")
        if self.check_if_ssid_exists(ssid):
            if self.strips_list_widgets[ssid - 1].get_type() is not StripEnum.Track:
                self.strips_list_widgets[ssid - 1].set_type(StripEnum.Bus) #has panner so it must be a bus
                if self.current_selected_bank_idx == self.strips_list_widgets[ssid - 1].get_bank():
                    self.emit('bank_channel_type_changed',
                              self.strips_list_widgets[ssid - 1].get_bank_index(),
                              self.strips_list_widgets[ssid - 1].get_type())

    def set_meter(self, ssid, value):
        if  self.check_if_ssid_exists(ssid):
            self.strips_list_widgets[ssid - 1].set_meter(value)
            #TODO!

    def strip_select(self, ssid, value, as_VCA = False):
        if  self.check_if_ssid_exists(ssid):
            if not self.send_mode:
                self.strips_list_widgets[ssid - 1].set_selected(value)

            # Check if bank has changed
            if value:  # Do not refresh the bank if selection is false
                if self.current_selected_bank_idx != self.strips_list_widgets[ssid - 1].get_bank(): #Only if bank changed

                    #Reset previous VCA ans Sends selection
                    if self.send_mode or self.vca_mode:
                        for i in range(0, len(self.strips_list_widgets)):
                            self.strips_list_widgets[i].set_bank_selected(False)
                            self.strips_list_widgets[i].set_selected(False)

                    self.current_selected_bank_idx = self.strips_list_widgets[ssid - 1].get_bank()

                self.current_selected_strip_widget_idx = ssid - 1

                #In VCA and SEND mode ensure to select the whole bank!
                if self.vca_mode or self.send_mode:
                    for i in range(self.current_selected_bank_idx*self.bank_size, self.current_selected_bank_idx*self.bank_size + self.bank_size ):
                        #print(f"VCA mode sel ssid is '{ssid}' and for i is '{i}'")
                        self.strips_list_widgets[i].set_selected(value)
                        self._emit_all_bank_signals(i + 1)

            #Send the select bank signal
            if self.current_selected_bank_idx ==  self.strips_list_widgets[ssid - 1].get_bank():
                self.emit('bank_channel_select_changed',
                          self.strips_list_widgets[ssid - 1].get_bank_index(),
                          self.strips_list_widgets[ssid - 1].get_selected())

    def on_strip_selected(self, widget, issid):
        self.emit('strip_select_changed', issid)

    def on_meter_refresh_timeout(self):
        for stripCtl in self.strips_list_widgets:
            stripCtl.refresh_meter()
        GLib.timeout_add(self.timeout_meter_interval, self.on_meter_refresh_timeout)

    def check_if_ssid_exists(self, issid):
        return  issid > 0 and issid <= len(self.strips_list_widgets)

    def reset_current_selected_bank(self):
        self.current_selected_bank_idx = None

    def _emit_all_bank_signals(self, ssid):
        self.emit('bank_channel_ssid_name_changed',
                  self.strips_list_widgets[ssid - 1].get_bank_index(),
                  self.strips_list_widgets[ssid - 1].get_ssid(),
                  self.strips_list_widgets[ssid - 1].get_name())

        self.emit('bank_channel_type_changed',
                  self.strips_list_widgets[ssid - 1].get_bank_index(),
                  self.strips_list_widgets[ssid - 1].get_type())

        self.emit('bank_channel_mute_changed',
                  self.strips_list_widgets[ssid - 1].get_bank_index(),
                  self.strips_list_widgets[ssid - 1].get_mute())

        if not self.send_mode:
            # In send mode we do not send solo and rec
            self.emit('bank_channel_solo_changed',
                      self.strips_list_widgets[ssid - 1].get_bank_index(),
                      self.strips_list_widgets[ssid - 1].get_solo())

            if (self.strips_list_widgets[ssid - 1].get_type() is StripEnum.Track):
                self.emit('bank_channel_rec_changed',
                          self.strips_list_widgets[ssid - 1].get_bank_index(),
                          self.strips_list_widgets[ssid - 1].get_rec())

        if self.strips_list_widgets[ssid - 1].get_fader() is not None:
            self.emit('bank_channel_fader_changed',
                      self.strips_list_widgets[ssid - 1].get_bank_index(),
                      self.strips_list_widgets[ssid - 1].get_fader())

        if self.strips_list_widgets[ssid - 1].get_fader_gain() is not None:
            self.emit('bank_channel_fader_gain_changed',
                      self.strips_list_widgets[ssid - 1].get_bank_index(),
                      self.strips_list_widgets[ssid - 1].get_fader_gain())

        else:
            self.emit('bank_channel_type_changed', self.strips_list_widgets[ssid - 1].get_bank_index(), 0.0)
            self.emit('bank_channel_fader_changed', self.strips_list_widgets[ssid - 1].get_bank_index(), 0.0)

        self.emit('bank_channel_select_changed',
                  self.strips_list_widgets[ssid - 1].get_bank_index(),
                  self.strips_list_widgets[ssid - 1].get_selected())
