"""
A widget conntaining multiple stripselwidgets in a Gtk.Grid
"""

from gi.repository import Gtk, GObject, GLib
import math
from stripselwidget import StripSelWidget
from stripTypes import StripEnum

class StripTable(Gtk.ScrolledWindow):
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

    def __init__(self, bank_size, meter_pixels_x_seconds = None, is_send = False, is_vca = False):
        super(StripTable, self).__init__()

        self.strips_list_widgets = [] #Stores the list of select widgets
        self.strips_ssid_id_dict = dict() #A dictornary to fastly acces select strip index from an ssid
        self.bank_strip_id_list = [] #Stores the strip indexes (id) for each bank index
        self.bank_size = bank_size
        self.current_selected_strip_widget = None
        self.current_selected_bank = None
        self.send_mode = is_send
        self.vca_mode = is_vca

        self.table = Gtk.Label(label="Strip list is empty, click the refresh button to start DAW comunication")
        self.viewport_table = Gtk.Viewport()
        self.viewport_table.add(self.table)
        self.add(self.viewport_table)

        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Meters, global refresh timer
        if meter_pixels_x_seconds is not None:
            self.timeout_meter_interval = round(1000.0 / meter_pixels_x_seconds)  # Timeout interval in milliseconds
            GLib.timeout_add(self.timeout_meter_interval, self.on_meter_refresh_timeout)

    def get_number_of_strips(self):
        return len(self.strips_list_widgets)

    def get_current_selected_strip_index(self):
        return self.current_selected_strip_widget

    def get_current_selected_strip_ssid(self):
        if self.current_selected_strip_widget is None:
            return None
        return self.strips_list_widgets[self.current_selected_strip_widget].get_ssid()

    def get_strip_ssid(self, index):
        return self.strips_list_widgets[index].get_ssid()

    def append_strip(self, ssid, name, type, mute, solo, rec, inputs, outputs):
        self.strips_ssid_id_dict[ssid] = len(self.strips_list_widgets)
        if self.send_mode:
            self.strips_list_widgets.append(StripSelWidget(len(self.strips_list_widgets),
                                                           ssid,
                                                           len(self.strips_list_widgets) // self.bank_size,
                                                           len(self.strips_list_widgets) % self.bank_size,
                                                           name,
                                                           type,
                                                           mute,
                                                           solo,
                                                           inputs,
                                                           outputs,
                                                           rec, True))
        else:
            self.strips_list_widgets.append(StripSelWidget(len(self.strips_list_widgets),
                                                                      ssid,
                                                                      len(self.strips_list_widgets) // self.bank_size,
                                                                      len(self.strips_list_widgets) % self.bank_size,
                                                                      name,
                                                                      type,
                                                                      mute,
                                                                      solo,
                                                                      inputs,
                                                                      outputs,
                                                                      rec))

        if self.strips_list_widgets[len(self.strips_list_widgets) - 1].get_bank_index() == 0:
            self.bank_strip_id_list.append([None] * self.bank_size) #New bank just added, so add an element to the bank list

        (self.bank_strip_id_list[self.strips_list_widgets[len(self.strips_list_widgets) - 1].get_bank()])[self.strips_list_widgets[len(self.strips_list_widgets) - 1].get_bank_index()] = self.strips_list_widgets[len(self.strips_list_widgets) - 1].get_index()


    def clear_strips(self):
        #if self.get_number_of_strips() > 0:
        self.strips_list_widgets = []  # Clear the list
        self.strips_ssid_id_dict = dict()  # Clear the id ssid dictionary
        self.bank_strip_id_list = [] #Clear the bank id list
        self.current_selected_strip_widget = None
        self.current_selected_bank = None
        if self.viewport_table.get_child() is not None:
            self.viewport_table.remove(self.table)

    def fill_strips(self):
        self.table = Gtk.Grid()
        self.table.set_row_spacing(5)
        self.table.set_column_homogeneous(True)
        self.viewport_table.add(self.table)

        for i in range(0, len(self.strips_list_widgets)):
            self.table.attach(self.strips_list_widgets[i],
                              i - self.bank_size * self.strips_list_widgets[i].get_bank(),
                              self.strips_list_widgets[i].get_bank(),
                              1,
                              1)
            self.strips_list_widgets[i].connect("strip_selected", self.on_strip_selected)

        if len(self.strips_list_widgets) < self.bank_size:
            # Insert empty columns to fill at least self.bank_size columns, use and empty label to achive that
            for i in range(len(self.strips_list_widgets), self.bank_size):
                self.table.attach(Gtk.Label(), i, 0, 1, 1)

        if len(self.strips_list_widgets) > 0:
            self.table.show_all()
            self.table.show()
        else:
            self.clear_strips()

    def set_strip_name(self, ssid, name):
        if ssid in self.strips_ssid_id_dict:
            idx = self.strips_ssid_id_dict[ssid]
            self.strips_list_widgets[idx].set_name(name)
            if self.current_selected_bank == self.strips_list_widgets[idx].get_bank():
                self.emit('bank_channel_ssid_name_changed', self.strips_list_widgets[idx].get_bank_index(), ssid, name)

    def set_fader(self, ssid, value):
        if ssid in self.strips_ssid_id_dict:
            idx = self.strips_ssid_id_dict[ssid]
            self.strips_list_widgets[idx].set_fader(value)  # Store fader, used in send mode
            bank_num = self.strips_list_widgets[idx].get_bank()
            if self.current_selected_bank == bank_num:
                self.emit('bank_channel_fader_changed', self.strips_list_widgets[idx].get_bank_index(), value)

    def set_fader_gain(self, ssid, value):
        if ssid in self.strips_ssid_id_dict:
            idx = self.strips_ssid_id_dict[ssid]

            #TODO trying to diable here 2 see if its this!
            self.strips_list_widgets[idx].set_fader_gain(value)  # Store fader gain, used in send mode
            bank_num = self.strips_list_widgets[idx].get_bank()
            if self.current_selected_bank == bank_num:
                self.emit('bank_channel_fader_gain_changed', self.strips_list_widgets[idx].get_bank_index(), value)

    def set_solo(self, ssid, value):
        if ssid in self.strips_ssid_id_dict:
            idx = self.strips_ssid_id_dict[ssid]
            self.strips_list_widgets[idx].set_solo(value)
            if self.current_selected_bank == self.strips_list_widgets[idx].get_bank():
                self.emit('bank_channel_solo_changed', self.strips_list_widgets[idx].get_bank_index(), value)

    def set_mute(self, ssid, value):
        if ssid in self.strips_ssid_id_dict:
            idx = self.strips_ssid_id_dict[ssid]
            self.strips_list_widgets[idx].set_mute(value)
            if self.current_selected_bank == self.strips_list_widgets[idx].get_bank():
                self.emit('bank_channel_mute_changed', self.strips_list_widgets[idx].get_bank_index(), value)

    def set_rec(self, ssid, value):
        if ssid in self.strips_ssid_id_dict:
            idx = self.strips_ssid_id_dict[ssid]
            self.strips_list_widgets[idx].set_rec(value)
            if self.current_selected_bank == self.strips_list_widgets[idx].get_bank():
                self.emit('bank_channel_rec_changed', self.strips_list_widgets[idx].get_bank_index(), value)

    def set_meter(self, ssid, value):
        if ssid in self.strips_ssid_id_dict:
            idx = self.strips_ssid_id_dict[ssid]
            self.strips_list_widgets[idx].set_meter(value)

    def hide_strip(self, ssid):
        if ssid in self.strips_ssid_id_dict:
            idx = self.strips_ssid_id_dict[ssid]
            self.strips_list_widgets[idx].set_sensitive(False)
            self.strips_list_widgets[idx].hide_child()

    def show_strip(self, ssid):
        if ssid in self.strips_ssid_id_dict:
            idx = self.strips_ssid_id_dict[ssid]
            self.strips_list_widgets[idx].set_sensitive(True)
            self.strips_list_widgets[idx].show_child()


    def strip_select(self, ssid, value):
        if ssid in self.strips_ssid_id_dict:
            idx = self.strips_ssid_id_dict[ssid]

            if not self.send_mode:
                self.strips_list_widgets[idx].set_selected(value)

            # Check if bank has changed
            if value:  # Do not refresh the bank if selection is false
                if self.current_selected_bank != self.strips_list_widgets[idx].get_bank(): #Only if bank changed

                    #Change previous selected bank state
                    if self.current_selected_bank is not None:
                        for i in self.bank_strip_id_list[self.current_selected_bank]:
                            if i is not None:
                                self.strips_list_widgets[i].set_bank_selected(False)
                                if self.send_mode or self.vca_mode:
                                    self.strips_list_widgets[i].set_selected(False)

                    self.current_selected_bank = self.strips_list_widgets[idx].get_bank()

                    #Bank changed so emit all signals to configure the new bank
                    for i in range(0, self.bank_size):
                        strip_index = (self.bank_strip_id_list[self.current_selected_bank])[i]

                        if strip_index is not None:
                            if self.strips_list_widgets[strip_index].get_bank_index() != i:
                                exit("FATAL ERROR: bank index lost!")

                            self.strips_list_widgets[strip_index].set_bank_selected(True)
                            if self.send_mode or self.vca_mode:
                                self.strips_list_widgets[strip_index].set_selected(True)

                            self.emit('bank_channel_ssid_name_changed',
                                      i,
                                      self.strips_list_widgets[strip_index].get_ssid(),
                                      self.strips_list_widgets[strip_index].get_name())

                            self.emit('bank_channel_type_changed',
                                      i,
                                      self.strips_list_widgets[strip_index].get_type())

                            self.emit('bank_channel_mute_changed',
                                      i,
                                      self.strips_list_widgets[strip_index].get_mute())

                            if not self.send_mode:
                                #In send mode we do not send solo and rec
                                self.emit('bank_channel_solo_changed',
                                          i,
                                          self.strips_list_widgets[strip_index].get_solo())


                                if (self.strips_list_widgets[strip_index].get_type() is StripEnum.AudioTrack) or (
                                        self.strips_list_widgets[strip_index].get_type() is StripEnum.MidiTrack):
                                    self.emit('bank_channel_rec_changed',
                                              i,
                                              self.strips_list_widgets[strip_index].get_rec())

                            if self.send_mode or self.vca_mode:
                                if self.strips_list_widgets[strip_index].get_fader() is not None:
                                    #In send and VCA modes we need to send fader values
                                    self.emit('bank_channel_fader_changed',
                                              i,
                                              self.strips_list_widgets[strip_index].get_fader())

                                    self.emit('bank_channel_fader_gain_changed',
                                              i,
                                              self.strips_list_widgets[strip_index].get_fader_gain())

                        else:
                            self.emit('bank_channel_type_changed', i, 0)
                            self.emit('bank_channel_fader_changed', i, 0)

                self.current_selected_strip_widget = idx

            #Send the select bank signal idependenly if bank has changed or not
            if self.current_selected_bank ==  self.strips_list_widgets[idx].get_bank():
                self.emit('bank_channel_select_changed',
                          self.strips_list_widgets[idx].get_bank_index(),
                          self.strips_list_widgets[idx].get_selected())

    def on_strip_selected(self, widget, issid):
        self.emit('strip_select_changed', issid)

    def on_meter_refresh_timeout(self):
        for stripCtl in self.strips_list_widgets:
            stripCtl.refresh_meter()
        GLib.timeout_add(self.timeout_meter_interval, self.on_meter_refresh_timeout)

    def check_if_ssid_exists(self, issid):
        return  issid in self.strips_ssid_id_dict

    def reset_current_selected_bank(self):
        self.current_selected_bank = None