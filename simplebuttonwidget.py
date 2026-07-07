"""
Definition of a two-state simple button able to handle ardour LED state and send ardour button booleans.
"""

from gi.repository import Gtk, GObject, Gdk
import math
import cairo
import colorsys
from enum import Enum


class ButtonType(Enum):
    TEXT_LABEL = 0
    PHASE_SYMBOL = 1


class SimpleButton(Gtk.EventBox):
    __gsignals__ = {
        'clicked': (GObject.SIGNAL_RUN_LAST, None, ())
    }

    def __init__(self, text="", color="#FFFFFF", type=ButtonType.TEXT_LABEL):
        super(SimpleButton, self).__init__()
        self.active_state = False
        self.label = text
        self.type = type
        self.color_active = Gdk.RGBA()
        self.color_active.parse(color)

        hsvColor = colorsys.rgb_to_hsv(self.color_active.red, self.color_active.green, self.color_active.blue)
        rgbColor = colorsys.hsv_to_rgb(hsvColor[0], hsvColor[1] * 0.4, hsvColor[2] * 0.5)
        self.color_inactive = Gdk.RGBA()
        self.color_inactive.red = rgbColor[0]
        self.color_inactive.green = rgbColor[1]
        self.color_inactive.blue = rgbColor[2]

        hsvColor = colorsys.rgb_to_hsv(self.color_active.red, self.color_active.green, self.color_active.blue)
        rgbColor = colorsys.hsv_to_rgb(hsvColor[0], hsvColor[1] * 0.6, hsvColor[2] * 1.2)
        self.color_brigth = Gdk.RGBA()
        self.color_brigth.red = rgbColor[0]
        self.color_brigth.green = rgbColor[1]
        self.color_brigth.blue = rgbColor[2]

        self.darea = Gtk.DrawingArea()
        self.darea.connect("draw", self.on_draw)
        self.add(self.darea)
        self.set_size_request(60, 60)

        # And bind an action to it
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self.button_press)

    def button_press(self, widget, event):
        if event.button == 1:
            self.emit("clicked")

    def set_active_state(self, bvalue):
        self.active_state = bvalue
        self.queue_draw()

    def get_active_state(self):
        return self.active_state

    def set_label(self, text):
        self.label = text
        self.queue_draw()

    def on_draw(self, area, cr):
        w = area.get_allocated_width()
        h = area.get_allocated_height()
        border = 2
        radius = 5

        cr.set_line_width(3)
        cr.set_source_rgb(0.1, 0.1, 0.1)  # Color of the border line

        cr.arc(border + radius, border + radius, radius, math.pi, 3.0 * math.pi / 2.0)
        cr.line_to(w - border - radius, border)
        cr.arc(w - border - radius, border + radius, radius, 3.0 * math.pi / 2.0, 0.0)
        cr.line_to(w - border, h - border - radius)
        cr.arc(w - border - radius, h - border - radius, radius, 0.0, math.pi / 2.0)
        cr.line_to(border + radius, h - border)
        cr.arc(border + radius, h - border - radius, radius, math.pi / 2.0, math.pi)
        cr.close_path()
        cr.stroke_preserve()

        # Always paint the background in off mode
        cr.set_source_rgb(self.color_inactive.red, self.color_inactive.green, self.color_inactive.blue)
        if self.active_state:
            cr.fill_preserve()
        else:
            cr.fill()

        # Add the LED effec if enabled
        if self.active_state:
            LGrad = cairo.RadialGradient((w / 2.0) - 20.0, (h / 2.0) - 15.0, 1.0, (w / 2.0) - 20.0, (h / 2.0) - 15.0,
                                         55.0)
            LGrad.add_color_stop_rgba(0.0, self.color_brigth.red, self.color_brigth.green, self.color_brigth.blue, 0.8)
            LGrad.add_color_stop_rgba(0.8, self.color_active.red, self.color_active.green, self.color_active.blue, 0.9)
            LGrad.add_color_stop_rgba(1.0, self.color_active.red, self.color_active.green, self.color_active.blue, 0.7)
            cr.set_source(LGrad)
            cr.fill()

        cr.set_source_rgb(0.21, 0.2, 0.17)
        if self.type is ButtonType.TEXT_LABEL:
            # Label
            lines = self.label.split('\n')

            cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(16)


            #txt_x, txt_y, txt_w, txt_h, txt_dx, txt_dy = cr.text_extents(self.label)
            _, _, _, line_h, _, _ = cr.text_extents("X")
            line_spacing = 20  # Pixels of padding between lines
            total_h = (line_h * len(lines)) + (line_spacing * (len(lines) - 1))
            start_y = (h / 2.0) - (total_h / 2.0) + line_h

            for i, line in enumerate(lines):
                # Calculate unique X for each line so they are individually centered horizontally
                _, _, txt_w, _, _, _ = cr.text_extents(line)
                x = (w / 2.0) - (txt_w / 2.0)

                # Push Y down for every subsequent line
                y = start_y + (i * (line_h + line_spacing))

                cr.move_to(x, y)
                cr.show_text(line)

            #cr.move_to(w / 2.0 - txt_w / 2.0, h / 2.0 + txt_h / 2.0)
            #cr.show_text(self.label)

        elif self.type is ButtonType.PHASE_SYMBOL:
            cr.set_line_width(4)
            myRadius = 12
            cr.move_to( (w / 2.0) + myRadius, (h / 2.0) )
            cr.arc(w / 2.0, h / 2.0, myRadius, 0.0, 2.0*math.pi)
            cr.move_to((w / 2.0) - 1.2*myRadius, (h / 2.0) + 1.2*myRadius)
            cr.line_to((w / 2.0) + 1.2 * myRadius, (h / 2.0) - 1.2 * myRadius)
            cr.stroke()


