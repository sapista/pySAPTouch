import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import cairo


class FastLabel(Gtk.DrawingArea):
	def __init__(self, text="", font_size=11, align="center"):
		super().__init__()

		self._text = text
		self._next_text = text
		self._font_size = font_size
		self._align = align  # "left", "center", "right"
		self.text_color = (0.9, 0.9, 0.9, 1.0)

		self.connect("draw", self._on_draw)
		self.set_size_request(50, 20)

		#Redraw timer
		self.bTimmerActive = False

	def update_label_timeout(self):
		if self._text != self._next_text:
			self._text = self._next_text
			self.queue_draw()
		self.bTimmerActive = False

		# Single shot timer
		return False

	def set_text(self, text):
		self._next_text = str(text)
		if self.bTimmerActive:
			return

		self._text = self._next_text
		self.queue_draw()
		self.bTimmerActive = True
		GLib.timeout_add(200, self.update_label_timeout)

	def get_text(self):
		return self._text

	def set_text_color(self, r, g, b, a=1.0):
		self.text_color = (r, g, b, a)
		self.queue_draw()

	def _on_draw(self, widget, cr):
		# Limpiar fondo (opcional, si quieres que sea transparente borra estas líneas)
		# cr.set_source_rgba(0.1, 0.1, 0.1, 1.0) # Fondo oscuro opcional
		# cr.paint()

		# Configurar fuente y color
		cr.set_source_rgba(*self.text_color)
		cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
		cr.set_font_size(self._font_size)

		# Obtener dimensiones actuales del widget
		allocation = self.get_allocation()
		width = allocation.width
		height = allocation.height

		# Medir las dimensiones métricas del texto para alinear
		extents = cr.text_extents(self._text)
		text_width = extents.width
		text_height = extents.height
		xbearing = extents.x_bearing

		# Calcular posición X según la alineación
		if self._align == "center":
			x = (width - text_width) / 2 - xbearing
		elif self._align == "right":
			x = width - text_width - xbearing - 4  # pequeño margen derecho
		else:  # "left"
			x = 4 - xbearing  # pequeño margen izquierdo

		# Calcular posición Y para centrarlo verticalmente de forma precisa
		y = (height / 2) + (text_height / 2)

		# Dibujar el texto en pantalla a velocidad de hardware
		cr.move_to(x, y)
		cr.show_text(self._text)

		return False