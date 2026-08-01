from gi.repository import GLib, Gtk

class OSCConnectionWatchdog:
	def __init__(self, callback):
		"""
		:param callback: Function to call when the watchdog expires
		"""
		self.timeout_seconds_connected_mode = 5000 # 5 seconds
		self.timeout_seconds_offline_mode = 2000 #When non-connected will trigger the timer more often
		self.callback = callback
		self._timer_id = None
		self.bOnline = False
		self.bFirstRun = True #The first time it will trigger really quick

	def start(self):
		"""Starts or resets (kicks) the watchdog timer."""
		# Cancel existing pending timer if any
		self.stop()

		# Schedule the callback
		timeout = self.timeout_seconds_offline_mode
		if self.bOnline:
			timeout = self.timeout_seconds_connected_mode
		if self.bFirstRun:
			self.bFirstRun = False
			timeout = 100

		self._timer_id = GLib.timeout_add(
			timeout,
			self._on_timeout
		)

	def reset(self):
		"""Alias for start() — 'kicking' or feeding the watchdog."""
		self.start()

	def stop(self):
		"""Stops the watchdog without triggering the callback."""
		if self._timer_id is not None:
			GLib.source_remove(self._timer_id)
			self._timer_id = None

	def set_OSC_online(self, bOSC_Connected):
		self.bOnline = bOSC_Connected
		self.reset()

	def get_OSC_online(self):
		return self.bOnline

	def _on_timeout(self):
		"""Internal callback when timer expires."""
		self._timer_id = None
		self.callback()
		# Returning False tells GLib NOT to repeat this timer automatically
		return False