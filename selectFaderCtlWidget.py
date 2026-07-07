"""
A widget to handle fader state of the selected channel.
This widget can control the fader, trim gain and sends but not the stereo panner
This widgets includes automation state contorls
"""

from gi.repository import Gtk, GObject
import simplebuttonwidget
import customframewidget
import pannerWidget
from automationTypes import AutomationModes

MAX_TRACK_NAME_LENGTH = 15

class SelectFaderCtlWidget(customframewidget.CustomFrame):
    __gsignals__ = {
        'automation_changed': (GObject.SIGNAL_RUN_LAST, None,
                               (int,)), #TODO I will need the sendID for the send bank!

        'send_active_changed': (GObject.SIGNAL_RUN_LAST, None,
                                (int, bool,)), #sendID, value
    }

    def __init__(self, name, isPanner = False, isSend = False):
        super(SelectFaderCtlWidget, self).__init__(0)

        self.sendID = None
        self.automation_mode = AutomationModes.NOT_SET
        self.isSend = isSend
        self.vbox = Gtk.VBox()
        self.lbl_title = Gtk.Label()
        self.set_name_label(name)
        self.vbox.pack_start(self.lbl_title, expand=True, fill=True, padding=0)

        if isSend:
            self.btn_Active = simplebuttonwidget.SimpleButton("ON", "#00FF00")
            self.btn_Active.connect("clicked", self.active_clicked)
            self.btn_Active.set_hexpand(True)

        if isPanner:
            self.lbl_dBvalue = None
            self.pannerWidget = pannerWidget.PannerWidget()
            self.vbox.pack_start(self.pannerWidget, expand=True, fill=True, padding=0)
        else:
            self.lbl_dBvalue = Gtk.Label()
            self.lbl_dBvalue.set_text("##.# dB")
            self.vbox.pack_start(self.lbl_dBvalue, expand=True, fill=True, padding=0)
            self.pannerWidget = None

        self.table_automationModes = Gtk.Grid()
        self.vbox.pack_start(self.table_automationModes, expand=True, fill=True, padding=0)

        self.btn_Manual = simplebuttonwidget.SimpleButton("Manual", "#E77700")
        self.btn_Manual.set_hexpand(True)
        self.btn_Play = simplebuttonwidget.SimpleButton("Play", "#E77700")
        self.btn_Write = simplebuttonwidget.SimpleButton("Write", "#E77700")
        self.btn_Touch = simplebuttonwidget.SimpleButton("Touch", "#E77700")
        self.btn_Latch = simplebuttonwidget.SimpleButton("Latch", "#E77700")

        if isPanner:
            self.table_automationModes.attach(self.btn_Manual, 0, 0, 1, 1)
            self.table_automationModes.attach(self.btn_Play, 1, 0, 1, 1)
            self.table_automationModes.attach(self.btn_Write, 2, 0, 1, 1)
            self.table_automationModes.attach(self.btn_Touch, 3, 0, 1, 1)
            self.table_automationModes.attach(self.btn_Latch, 4, 0, 1, 1)
        else:
            if isSend:
                self.table_automationModes.attach(self.btn_Active, 0, 0, 1, 1)
                self.table_automationModes.attach(self.btn_Manual, 1, 0, 1, 1)
            else:
                self.table_automationModes.attach(self.btn_Manual, 0, 0, 2, 1)
            self.table_automationModes.attach(self.btn_Play, 0, 1, 1, 1)
            self.table_automationModes.attach(self.btn_Write, 1, 1, 1, 1)
            self.table_automationModes.attach(self.btn_Touch, 0, 2, 1, 1)
            self.table_automationModes.attach(self.btn_Latch, 1, 2, 1, 1)

        if isPanner:
            self.HBox_panner_lbls = Gtk.HBox()
            self.lbl_pan_pos = Gtk.Label()
            self.lbl_pan_pos.set_markup("<span weight='bold' font_desc='Arial 14'>Position</span>")
            self.HBox_panner_lbls.pack_start(self.lbl_pan_pos, expand=True, fill=True, padding=0)
            self.lbl_pan_width = Gtk.Label()
            self.lbl_pan_width.set_markup("<span weight='bold' font_desc='Arial 14'>Width</span>")
            self.HBox_panner_lbls.pack_start(self.lbl_pan_width, expand=True, fill=True, padding=0)
            self.vbox.pack_start(self.HBox_panner_lbls, expand=True, fill=True, padding=0)


        self.add(self.vbox)
        self.vbox.set_border_width(7)

        self.btn_Manual.connect("clicked", self.manual_clicked)
        self.btn_Play.connect("clicked", self.play_clicked)
        self.btn_Write.connect("clicked", self.write_clicked)
        self.btn_Touch.connect("clicked", self.touch_clicked)
        self.btn_Latch.connect("clicked", self.latch_clicked)

    def set_name_label(self, name):
        if self.isSend:
            name = "Send: " + name
        if len(name) > MAX_TRACK_NAME_LENGTH:
            name = name[:MAX_TRACK_NAME_LENGTH] + "..."

        self.lbl_title.set_markup("<span weight='bold' font_desc='Arial 16'>" + name + "</span>")

    def set_gain_label(self, value):
        if self.lbl_dBvalue is not None:
            self.lbl_dBvalue.set_text(str(round(value, 1)) + " dB")

    def set_panner_position(self, value):
        if self.pannerWidget is not None:
            self.pannerWidget.set_position(value)

    def set_panner_width(self, value):
        if self.pannerWidget is not None:
            self.pannerWidget.set_width(value)

    def set_sendID(self, ID):
        if self.isSend:
            self.sendID = ID

    def get_sendID(self):
        return self.sendID

    def set_automation_mode(self, value):
        self.automation_mode = AutomationModes(value)
        self.btn_Manual.set_active_state(False)
        self.btn_Play.set_active_state(False)
        self.btn_Write.set_active_state(False)
        self.btn_Touch.set_active_state(False)
        self.btn_Latch.set_active_state(False)

        if self.automation_mode == AutomationModes.MANUAL:
            self.btn_Manual.set_active_state(True)
        elif self.automation_mode == AutomationModes.PLAY:
            self.btn_Play.set_active_state(True)
        elif self.automation_mode == AutomationModes.WRITE:
            self.btn_Write.set_active_state(True)
        elif self.automation_mode == AutomationModes.TOUCH:
            self.btn_Touch.set_active_state(True)
        elif self.automation_mode == AutomationModes.LATCH:
            self.btn_Latch.set_active_state(True)

        self.queue_draw()

    def get_automation_mode(self):
        return self.automation_mode.value

    def set_send_active(self, active):
        self.btn_Active.set_active_state(active)

    def active_clicked(self, widget):
        self.emit('send_active_changed', self.sendID, not self.btn_Active.get_active_state())

    def manual_clicked(self, widget):
        if self.automation_mode != AutomationModes.MANUAL:
            self.set_automation_mode(AutomationModes.MANUAL.value)
            self.emit('automation_changed', self.automation_mode.value)

    def play_clicked(self, widget):
        if self.automation_mode != AutomationModes.PLAY:
            self.set_automation_mode(AutomationModes.PLAY.value)
            self.emit('automation_changed', self.automation_mode.value)

    def write_clicked(self, widget):
        if self.automation_mode != AutomationModes.WRITE:
            self.set_automation_mode(AutomationModes.WRITE.value)
            self.emit('automation_changed', self.automation_mode.value)

    def touch_clicked(self, widget):
        if self.automation_mode != AutomationModes.TOUCH:
            self.set_automation_mode(AutomationModes.TOUCH.value)
            self.emit('automation_changed', self.automation_mode.value)

    def latch_clicked(self, widget):
        if self.automation_mode != AutomationModes.LATCH:
            self.set_automation_mode(AutomationModes.LATCH.value)
            self.emit('automation_changed', self.automation_mode.value)

    def hide(self):
        self.vbox.hide()

    def show(self):
        self.vbox.show()

