"""
Definition of a simple LED widget.
"""

from gi.repository import Gtk, Gdk
import cairo
import math

class LEDWidget(Gtk.DrawingArea):
    def __init__(self, txt_label, str_color):
        super(LEDWidget, self).__init__()
        self.connect("draw", self.on_draw)
        self.set_size_request(-1, 25)
        self.label = txt_label
        self.on = True
        self.color_on = Gdk.RGBA()
        self.color_on.parse(str_color)

    def set_value(self, value):
        self.on = value
        self.queue_draw()

    def get_value(self):
        return self.on

    def on_draw(self, area, cr):
        w = area.get_allocated_width()
        h = area.get_allocated_height()

        #Label text
        cr.set_source_rgb(1.0, 1.0, 1.0)  # Color for the text
        cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(11)
        txt_x, txt_y, txt_w, txt_h, txt_dx, txt_dy = cr.text_extents(self.label)
        cr.move_to( 22, h / 2.0 + txt_h / 2.0)
        cr.show_text(self.label)

        #LED
        cr.set_line_width(1.5)
        cr.set_source_rgb(1.0, 1.0, 1.0)  # Color for the text
        cr.move_to(20, h / 2.0)
        cr.arc(15, h / 2.0, 5.0, 0.0, 2.0 * math.pi)
        cr.close_path()
        cr.stroke_preserve()
        if self.on:
            #LED on using a nice gradient
            LedGradient = cairo.RadialGradient(14, (h / 2.0) - 1, 1.0, 14, (h / 2.0) - 1.0, 6.0)
            LedGradient. add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 1.0)
            LedGradient.add_color_stop_rgba(0.15, self.color_on.red, self.color_on.green, self.color_on.blue, 1.0)
            LedGradient.add_color_stop_rgba(1.0, self.color_on.red, self.color_on.green, self.color_on.blue, 0.6)
            cr.set_source(LedGradient)
        else:
            cr.set_source_rgba(self.color_on.red, self.color_on.green, self.color_on.blue, 0.2)  # Color for the LED OFF
        cr.fill()

