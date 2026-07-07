"""
Definition of custom Frame widget based on Gtk.Container.
"""

from gi.repository import Gtk, Gdk
import cairo
import math
from stripTypes import StripEnum
import colorsys

class CustomFrame(Gtk.Bin):

    def __init__(self, stripType):
        super(CustomFrame, self).__init__()
        self.selected = False
        self.bankSelected = False

        #Set strip color
        self.dirstripcolor = {StripEnum.Empty: '#353535',
                        StripEnum.AudioTrack: '#304057',
                        StripEnum.AudioBus: '#20242A',
                        StripEnum.MidiTrack: '#474F3F',
                        StripEnum.MidiBus: '#353B2F',
                        StripEnum.AuxBus: '#496183',
                        StripEnum.VCA: '#683030'}
        self.strip_color = Gdk.RGBA()
        self.strip_color.parse(self.dirstripcolor[stripType])

        #Set frame normal color
        hsvColor = colorsys.rgb_to_hsv(self.strip_color.red, self.strip_color.green, self.strip_color.blue)
        rgbColor = colorsys.hsv_to_rgb(hsvColor[0], hsvColor[1] * 1.5, hsvColor[2] * 1.8)
        self.frame_color = Gdk.RGBA()
        self.frame_color.red = rgbColor[0]
        self.frame_color.green = rgbColor[1]
        self.frame_color.blue = rgbColor[2]

        self.set_border_width(0)
        self.connect("draw", self.on_draw)

    def set_selected(self, bSelected):
        self.selected = bSelected
        self.queue_draw()

    def set_bank_selected(self, bBankSeleceted):
        self.bankSelected = bBankSeleceted
        self.queue_draw()

    def set_strip_type(self, stripType):
        self.strip_color.parse(self.dirstripcolor[stripType])
        self.queue_draw()

    def on_draw(self, area, cr):
        w = area.get_allocated_width()
        h = area.get_allocated_height()
        border = 4
        radius = 8

        #Select the whole bank
        if self.bankSelected:
            GradientBank = cairo.LinearGradient(0.0, 0.0, 0.0, h)
            GradientBank.add_color_stop_rgba(0, 0.0, 0.0, 0.0, 0.0)
            GradientBank.add_color_stop_rgba(0.1, 1.0, 1.0, 1.0, 1.0)
            GradientBank.add_color_stop_rgba(0.9, 1.0, 1.0, 1.0, 1.0)
            GradientBank.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
            cr.set_source(GradientBank)
            cr.rectangle(0.0, 0.0, w, h)
            cr.fill()

        #Draw the frame
        cr.set_line_width(4)
        if self.selected:
            cr.set_source_rgb(0.0, 1.0, 0.8)
        else:
            cr.set_source_rgb(self.frame_color.red, self.frame_color.green, self.frame_color.blue)
        cr.arc(border + radius, border + radius, radius, math.pi, 3.0 * math.pi / 2.0)
        cr.line_to(w - border - radius, border)
        cr.arc(w - border - radius, border + radius, radius, 3.0 * math.pi / 2.0, 0.0)
        cr.line_to(w - border, h - border - radius)
        cr.arc(w - border - radius, h - border - radius, radius, 0.0, math.pi / 2.0)
        cr.line_to(border + radius, h - border)
        cr.arc(border + radius, h - border - radius, radius, math.pi / 2.0, math.pi)
        cr.close_path()
        cr.stroke_preserve()

        GradientBackground = cairo.LinearGradient(0.0, 0.0, 0.0, h)
        GradientBackground.add_color_stop_rgb(0.0, self.strip_color.red, self.strip_color.green, self.strip_color.blue)
        GradientBackground.add_color_stop_rgb(1.0, 0.0, 0.0, 0.0)
        cr.set_source(GradientBackground)
        cr.fill()




