"""
Definition of a simple meter which displays a simplifed waveform.
"""

from gi.repository import Gtk

class MiniMeter(Gtk.DrawingArea):
    def __init__(self):
        super(MiniMeter, self).__init__()
        self.connect("draw", self.on_draw)
        self.connect("size-allocate", self.on_size_allocate)
        self.set_size_request(-1, 30)
        self.next_value = 0
        self.buffer = [0.0] * 10; #Starting with some arbitrary value

    def set_value(self, value):
        self.next_value = max(self.next_value, value)

    def refresh(self):
        #Shift register
        for i in range(0, len(self.buffer) - 1):
            self.buffer[i] = self.buffer[i+1]
        self.buffer[len(self.buffer)-1] = self.next_value
        self.next_value = self.next_value * 0.7 #fast and simple decay

        #redraw
        self.queue_draw()

    def on_draw(self, area, cr):
        w = area.get_allocated_width()
        h = area.get_allocated_height()

        # waveform color
        cr.set_source_rgb(0.46, 0.79, 0.43)
        for i in range(0, len(self.buffer)):
            cr.line_to(i+1, (2-h)*self.buffer[i] + h-1 )
        cr.line_to(w-1, h-1)
        cr.line_to(1, h-1)
        cr.close_path()
        cr.fill()

    def on_size_allocate(self, obj, allocation):
        self.buffer = [0.0] * (allocation.width - 2); #Redefine the buffer with the proper length
        self.queue_draw()

