#!/usr/bin/env python

import gi
import subprocess
import os
import socket
import sys

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GLib

# Get the absolute directory where launcher.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def is_debug_mode():
	# Checks standard trace or common IDE debugging modules in memory
	debugger_modules = {"pydevd", "debugpy", "pudb", "ipdb"}
	return sys.gettrace() is not None or any(mod in sys.modules for mod in debugger_modules)

class LauncherWindow(Gtk.Window):
	def __init__(self):
		super().__init__(title="SAPTouch Launcher")

		# Occupy the entire screen
		if is_debug_mode():
			print("Running in debug mode!")
			self.set_size_request(1280, 800)
		else:
			self.fullscreen()

		# Main container (Overlay)
		overlay = Gtk.Overlay()
		self.add(overlay)

		# Background
		logo_path = os.path.join(BASE_DIR, "logo/pibackground.png")
		if os.path.exists(logo_path):
			pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 1280, 800, True)
			image = Gtk.Image.new_from_pixbuf(pixbuf)
			image.set_valign(Gtk.Align.CENTER)
			image.set_halign(Gtk.Align.CENTER)
			overlay.add(image)
		else:
			fallback_label = Gtk.Label(label="[ Place logo.png here ]")
			fallback_label.set_valign(Gtk.Align.CENTER)
			fallback_label.set_halign(Gtk.Align.CENTER)
			overlay.add(fallback_label)

		# Button to start the app manually if needed
		fixed_container = Gtk.Fixed()
		overlay.add_overlay(fixed_container)
		button = Gtk.Button(label="Start SAPTouch")
		button.set_size_request(400, 140)

		button_css = Gtk.CssProvider()
		button_css.load_from_data(b"button { font-size: 32px; font-weight: bold; border-radius: 10px; border: 3px solid white; }")
		button.get_style_context().add_provider(button_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

		button.connect("clicked", self.on_button_clicked)

		# Place it precisely at X = 640, Y = 570
		fixed_container.put(button, 640 - 400/2, 570)

		# Bottom label with the Raspberry Pi's IP address
		self.ip_label = Gtk.Label()
		self.update_ip_label()  # Immediate initial load

		ip_css = Gtk.CssProvider()
		ip_css.load_from_data(b"label { font-size: 24px; color: #444444; font-weight: bold; }")
		self.ip_label.get_style_context().add_provider(ip_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

		self.ip_label.set_valign(Gtk.Align.END)
		self.ip_label.set_halign(Gtk.Align.CENTER)
		self.ip_label.set_margin_bottom(30)
		overlay.add_overlay(self.ip_label)

		# Schedule a timer to check the IP every 15 second
		GLib.timeout_add_seconds(15, self.on_timer_check_ip)

		# Check network on startup and launch app automatically if network is available
		GLib.idle_add(self.check_and_auto_launch)

	def get_ip_address(self):
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		try:
			s.settimeout(1)
			s.connect(('10.255.255.255', 1))
			ip = s.getsockname()[0]
		except Exception:
			ip = None
		finally:
			s.close()
		return ip

	def update_ip_label(self):
		ip = self.get_ip_address()
		if ip:
			self.ip_label.set_text(f"IP: {ip}")
		else:
			self.ip_label.set_text("No network connection")

	def on_timer_check_ip(self):
		self.update_ip_label()
		return True

	def run_main_app(self):
		self.hide()

		# Force GTK to process the hide event immediately before blocking with subprocess
		while Gtk.events_pending():
			Gtk.main_iteration()

		subprocess.run(
			["python3", "maingui.py"],
			cwd=BASE_DIR
		)

		# When the main app closes, refresh IP and bring the launcher back up
		self.update_ip_label()
		self.show()

	def check_and_auto_launch(self):
		ip = self.get_ip_address()
		if ip:
			print(f"Network detected (IP: {ip}). Launching application automatically...")
			self.run_main_app()
		else:
			print("No network detected on startup. Staying on launcher screen.")
		return False  # Return False so idle_add only runs once

	def on_button_clicked(self, widget):
		self.run_main_app()


if __name__ == "__main__":
	win = LauncherWindow()
	win.connect("destroy", Gtk.main_quit)
	win.show_all()
	Gtk.main()