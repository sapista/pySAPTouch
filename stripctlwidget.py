"""
Definition of a widget to handle all Ardour controls of a single strip.
8 widgets of this class will be layout horizontally to represent the current selected bank.
This class is responsible to deal with all events related with SPI or I2C fader controller.
"""

from gi.repository import Gtk, GObject
from stripTypes import StripEnum
import simplebuttonwidget
import customframewidget
import fastlabel

MAX_TRACK_NAME_LENGTH = 15


class StripCtlWidget(customframewidget.CustomFrame):
    __gsignals__ = {
        'strip_edit': (GObject.SIGNAL_RUN_LAST, None,
                           (int, )),

        'strip_selected': (GObject.SIGNAL_RUN_LAST, None,
                           (int, bool)),

        'solo_changed': (GObject.SIGNAL_RUN_LAST, None,
                         (int, bool)),

        'mute_changed': (GObject.SIGNAL_RUN_LAST, None,
                         (int, bool)),

        'rec_changed': (GObject.SIGNAL_RUN_LAST, None,
                        (int, bool)),

        'spill_changed': (GObject.SIGNAL_RUN_LAST, None,
                        (int, )),

        'fader_changed': (GObject.SIGNAL_RUN_LAST, None,
                          (int, float))
    }

    def __init__(self):
        super(StripCtlWidget, self).__init__(0)
        self.select = False
        self.solo = False
        self.mute = False
        self.rec = False

        self.vbox = Gtk.VBox()
        self.lbl_title = Gtk.Label()
        self.vbox.pack_start(self.lbl_title, expand=True, fill=True, padding=0)
        self.lbl_strip_type = fastlabel.FastLabel(font_size=11)
        self.vbox.pack_start(self.lbl_strip_type, expand=True, fill=True, padding=0)
        self.lbl_gain = fastlabel.FastLabel(font_size=14)
        self.lbl_gain.set_text("##.# dB")
        self.vbox.pack_start(self.lbl_gain, expand=True, fill=True, padding=0)

        self.table_selrecsolomute = Gtk.Grid()
        self.vbox.pack_start(self.table_selrecsolomute, expand=True, fill=True, padding=0)

        self.btn_edit = Gtk.Button()
        self.lbl_edit = Gtk.Label()
        self.lbl_edit.set_markup("<span weight='bold' font_desc='Arial 16'>Edit</span>")
        self.btn_edit.add(self.lbl_edit)
        self.btn_edit.set_hexpand(True)
        self.btn_edit.set_size_request(-1, 50)
        self.table_selrecsolomute.attach(self.btn_edit, 0, 0, 2, 1)
        self.btn_select = simplebuttonwidget.SimpleButton("SEL", "#FF9023")
        self.table_selrecsolomute.attach(self.btn_select, 0, 1, 1, 1)
        self.btn_rec = simplebuttonwidget.SimpleButton("REC", "#FF0000")
        self.table_selrecsolomute.attach(self.btn_rec, 1, 1, 1, 1)
        self.btn_solo = simplebuttonwidget.SimpleButton("SOLO", "#00FF00")
        self.btn_solo.set_hexpand(True)
        self.table_selrecsolomute.attach(self.btn_solo, 0, 2, 1, 1)
        self.btn_mute = simplebuttonwidget.SimpleButton("MUTE", "#FFFF00")
        self.btn_mute.set_hexpand(True)
        self.table_selrecsolomute.attach(self.btn_mute, 1, 2, 1, 1)
        self.btn_spill = simplebuttonwidget.SimpleButton("SPILL", "#FF9023")
        self.btn_spill.set_hexpand(True)
        self.btn_spill.set_size_request(-1, 50)
        self.table_selrecsolomute.attach(self.btn_spill, 0, 0, 2, 1)

        self.add(self.vbox)
        self.vbox.set_border_width(7)

        self.btn_edit.connect("clicked", self.edit_clicked)
        self.btn_select.connect("clicked", self.select_clicked)
        self.btn_solo.connect("clicked", self.solo_clicked)
        self.btn_mute.connect("clicked", self.mute_clicked)
        self.btn_rec.connect("clicked", self.rec_clicked)
        self.btn_spill.connect("clicked", self.spill_clicked)

        self.set_ssid_name(None, "")
        self.set_strip_type(StripEnum.Empty)
        self.set_size_request(-1, 120)

    def set_ssid_name(self, ssid, name):
        self.ssid = ssid
        if len(name) > MAX_TRACK_NAME_LENGTH:
            self.stripname = name[:MAX_TRACK_NAME_LENGTH] + "..."
        else:
            self.stripname = name
        if ssid is None:
            self.lbl_title.set_markup("")
        else:
            self.lbl_title.set_markup("<span weight='bold' size='medium'>" + self.stripname + "</span>")

    def set_strip_type(self, itype):
        self.type = itype

        #Set background color
        super(StripCtlWidget, self).set_strip_type(itype)

        # Set strip type label
        dirstriptype = {StripEnum.Empty: '',
                        StripEnum.AudioTrack: 'Audio Track',
                        StripEnum.AudioBus: 'Audio Bus',
                        StripEnum.MidiTrack: 'Midi Track',
                        StripEnum.MidiBus: 'Midi Bus',
                        StripEnum.AuxBus: 'Aux Bus',
                        StripEnum.VCA: 'VCA'}

        self.btn_edit.hide()
        self.btn_mute.hide()
        self.btn_solo.hide()
        self.btn_rec.hide()
        self.btn_select.hide()
        self.btn_spill.hide()
        self.btn_spill.set_active_state(False)
        self.lbl_strip_type.hide()
        self.lbl_title.hide()
        self.lbl_gain.hide()

        if self.type is not StripEnum.Empty:
            self.btn_mute.show()
            self.btn_solo.show()
            self.lbl_strip_type.show()
            self.lbl_title.show()
            self.lbl_gain.show()

        if self.type is StripEnum.AudioTrack or  self.type is StripEnum.MidiTrack:
            self.btn_rec.show()
            self.btn_edit.show()
            self.btn_select.show()

        if self.type is StripEnum.AudioBus or self.type is StripEnum.MidiBus:
            self.btn_edit.show()
            self.btn_select.show()

        if self.type is StripEnum.VCA:
            self.btn_spill.show()

        if self.ssid is None:
            self.lbl_strip_type.set_text("")
            self.lbl_gain.set_text("")
        else:
            self.lbl_strip_type.set_text(str(self.ssid) + "-" + dirstriptype[self.type])


    def set_select(self, bvalue):
        self.select = bvalue
        self.btn_select.set_active_state(self.select)

    def set_gain_label(self, value):
        self.lbl_gain.set_text(str(round(value, 1)) + " dB")

    def set_solo(self, bvalue):
        self.solo = bvalue
        self.btn_solo.set_active_state(self.solo)

    def set_mute(self, bvalue):
        self.mute = bvalue
        self.btn_mute.set_active_state(self.mute)

    def set_rec(self, bvalue):
        self.rec = bvalue
        self.btn_rec.set_active_state(self.rec)

    def edit_clicked(self, widget):
        self.select = True
        self.emit('strip_edit', self.ssid)

    def select_clicked(self, widget):
        self.select = not self.select
        self.emit('strip_selected', self.ssid, self.select)

    def solo_clicked(self, widget):
        self.solo = not self.solo
        self.emit('solo_changed', self.ssid, self.solo)

    def mute_clicked(self, widget):
        self.mute = not self.mute
        self.emit('mute_changed', self.ssid, self.mute)

    def rec_clicked(self, widget):
        self.rec = not self.rec
        self.emit('rec_changed', self.ssid, self.rec)

    def spill_clicked(self, widget):
        self.btn_spill.set_active_state(True)
        self.emit('spill_changed', self.ssid)

    def get_ssid(self):
        return self.ssid
