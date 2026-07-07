"""
Definition of a widget to display the panner state.
"""

from gi.repository import Gtk
import math
import cairo

class PannerWidget(Gtk.DrawingArea):

    def __init__(self):
        super(PannerWidget, self).__init__()
        self.set_size_request(-1, 60)
        self.position = 0.5
        self.width = 0.0
        self.connect("draw", self.on_draw)

    def set_position(self, position):
        self.position = position
        self.queue_draw()

    def set_width(self, width):
        self.width = width * 2.0 - 1.0 #Converting from Ardour 6.0 system between 0 to 1
        self.queue_draw()

    def on_draw(self, area, cr):
        w = area.get_allocated_width()
        h = area.get_allocated_height()
        border = 4
        radius = 8

        #Draw the frame and the background
        cr.set_line_width(2)
        cr.set_source_rgb(0.8, 0.8, 0.8)
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
        GradientBackground.add_color_stop_rgba(0.0, 0.1, 0.18, 0.21, 0.8)
        GradientBackground.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.5)
        cr.set_source(GradientBackground)
        cr.fill()

        cr.set_source_rgb(0.6, 0.6, 0.6)
        cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(16)
        txt_x, txt_y, txt_w, txt_h, txt_dx, txt_dy = cr.text_extents("L")
        cr.move_to(10, h - txt_h - 2)
        cr.show_text("L")

        cr.set_source_rgb(0.6, 0.6, 0.6)
        cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(16)
        txt_x, txt_y, txt_w, txt_h, txt_dx, txt_dy = cr.text_extents("R")
        cr.move_to(w - txt_w - 10, h - txt_h - 2)
        cr.show_text("R")

        MARGIN_X = 30
        MARGIN_Y = 10
        BALL_RADIUS = 18

        #Line connecting both balls
        plotWidth = self.width
        if self.width == 1.0 and self.position != 0.5:
            plotWidth = 0.0

        lpos = (self.position + (0.5 * plotWidth)) * (2 * MARGIN_X - w) + w - MARGIN_X
        rpos = (self.position - (0.5 * plotWidth)) * (2 * MARGIN_X - w) + w - MARGIN_X
        cr.set_line_width(8)
        cr.set_source_rgba(0.8, 0.8, 0.8, 0.5)
        cr.move_to(lpos,  (h / 2.0) - MARGIN_Y)
        cr.line_to(rpos,  (h / 2.0) - MARGIN_Y)
        cr.stroke()

        #Draw the Left ball
        cr.set_line_width(1.5)
        cr.set_source_rgb(0.8, 0.8, 0.8)
        cr.move_to(lpos + BALL_RADIUS , (h / 2.0) - MARGIN_Y)
        cr.arc(lpos, (h / 2.0) - MARGIN_Y, BALL_RADIUS, 0.0, 2.0 * math.pi)
        cr.close_path()
        cr.stroke_preserve()
        if plotWidth > 0 :
            cr.set_source_rgba(0.23, 0.43, 0.58, 1)
        elif plotWidth < 0 :
            cr.set_source_rgba(0.41, 0.15, 0.16, 1)
        else:
            cr.set_source_rgba(0.32, 0.51, 0.31, 1) #Mono/Balance mode
        cr.fill()
        cr.set_source_rgb(0.6, 0.6, 0.6)
        cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(18)
        txt_x, txt_y, txt_w, txt_h, txt_dx, txt_dy = cr.text_extents("L")
        cr.move_to(lpos - txt_w / 2.0, (h / 2.0) - MARGIN_Y + txt_h / 2.0)
        if plotWidth == 0.0:
            cr.show_text("P")
        else:
            cr.show_text("L")

        #Draw the Right ball
        if plotWidth != 0.0:
            cr.set_line_width(1.5)
            cr.set_source_rgb(0.8, 0.8, 0.8)
            cr.move_to(rpos + BALL_RADIUS , (h / 2.0) - MARGIN_Y)
            cr.arc(rpos, (h / 2.0) - MARGIN_Y, BALL_RADIUS, 0.0, 2.0 * math.pi)
            cr.close_path()
            cr.stroke_preserve()
            if plotWidth > 0 :
                cr.set_source_rgba(0.23, 0.43, 0.58, 1)
            else:
                cr.set_source_rgba(0.41, 0.15, 0.16, 1)
            cr.fill()
            cr.set_source_rgb(0.6, 0.6, 0.6)
            cr.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(18)
            txt_x, txt_y, txt_w, txt_h, txt_dx, txt_dy = cr.text_extents("R")
            cr.move_to(rpos - txt_w / 2.0, (h / 2.0) - MARGIN_Y + txt_h / 2.0)
            cr.show_text("R")

