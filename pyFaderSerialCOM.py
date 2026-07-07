#!/usr/bin/env python

import serial
import threading
from sys import exit
from gi.repository import GLib, GObject


class FaderCOM(GObject.GObject):

    __gsignals__ = {
        'fader_changed': (GObject.SIGNAL_RUN_FIRST, None,
                             (int, float)),  # channel, value

        'encoder_changed': (GObject.SIGNAL_RUN_FIRST, None,
                          (float,)),  # value

        'fader_untouched': (GObject.SIGNAL_RUN_FIRST, None,
                                (int,)),  # value

        'mute_button_changed': (GObject.SIGNAL_RUN_FIRST, None,
                          (int,)),  # value

        'solo_button_changed': (GObject.SIGNAL_RUN_FIRST, None,
                                (int,)),  # value

        'rec_button_changed': (GObject.SIGNAL_RUN_FIRST, None,
                                (int,)),  # value

        'sel_button_changed': (GObject.SIGNAL_RUN_FIRST, None,
                                (int,))  # value
    }

    def __init__(self, port, baudrate, fader_min, fader_max):
        GObject.GObject.__init__(self)
        self.FADER_MIN = fader_min
        self.FADER_MAX = fader_max
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baudrate
        self.ser.timeout = 1  # 1 second reading timeout to allow to stop the reading thread
        self.serial_polling = False

        try:
            self.ser.open()
            self.serial_read_thread = threading.Thread(target=self.readSerialPort)
            if not self.ser.is_open:
                exit('Error: not able to open serial port')
            else:
                self.serial_polling = True
                self.serial_read_thread.start()

        except serial.SerialException:
            # 2. If the hardware isn't plugged in, catch the crash!
            print("Warning: Serial Hardware not found. Creating dummy port to prevent crash. No fader module com!")

        # RX packet holder
        self.RX_packet = bytearray()

        #Button assiggments constants
        self.PICOMID_UNTOUCH   = 0x00
        self.PICOMID_MUTE    = 0x01
        self.PICOMID_SOLO    = 0x02
        self.PICOMID_REC	 = 0x03
        self.PICOMID_SELECT  = 0x04

    def moveFader(self, channel, value):
        position = int(value * (self.FADER_MAX - self.FADER_MIN) + self.FADER_MIN ) #Float to int conversion
        if (channel > 7) or (channel < 0):
            exit("Error: Fader channel must be an integer from 0 to 7")
        if position > self.FADER_MAX :
            position = self.FADER_MAX
        if position < self.FADER_MIN:
            position = self.FADER_MIN
        byte1 = 0x40 | (channel << 3) | ((position & 0x380) >> 7)
        byte2 = 0x80 | (position & 0x7F)

        packet = bytearray()
        packet.append(byte1)
        packet.append(byte2)

        if self.ser.is_open:
            self.ser.write(packet)

    def readSerialPort(self):
        while self.serial_polling:
            RX_byte = self.ser.read(1)
            if len(RX_byte) > 0:
                if RX_byte[0] & 0x80:
                    # We are receiving the second byte
                    if len(self.RX_packet) == 1:
                        # Process the second byte
                        self.RX_packet.append(RX_byte[0])
                    else:
                        # corrupted frame so start over
                        self.RX_packet.clear()
                else:
                    # We are receiving the first byte
                    self.RX_packet.clear()
                    self.RX_packet.append(RX_byte[0])

                if len(self.RX_packet) == 2:
                    # complete packet, so process it!
                    self.decodeIncomingPacket()

    def decodeIncomingPacket(self):
        if self.RX_packet[0] & 0x40:
            # we got a fader message
            channel = int((self.RX_packet[0] & 0x38) >> 3);
            value = (int(self.RX_packet[0] & 0x07) << 7) | (int(self.RX_packet[1] & 0x7F));
            if value > self.FADER_MAX:
                value = self.FADER_MAX
            if value < self.FADER_MIN:
                value = self.FADER_MIN
            value = (value/(self.FADER_MAX - self.FADER_MIN)) - (self.FADER_MIN/(self.FADER_MAX - self.FADER_MIN))
            GLib.idle_add(self.emit, 'fader_changed', channel, value) #Emit with to float conversion

        else:
            if self.RX_packet[0] & 0x20:
                # we got an encoder message
                value = int(self.RX_packet[1] & 0x7F) | int((self.RX_packet[0] & 0x1) << 7);
                value = int.from_bytes(value.to_bytes(1, byteorder='big', signed=False), byteorder='big', signed=True)
                GLib.idle_add(self.emit, 'encoder_changed', float(value)) #Emit with to float conversion
            else:
                # we got a untouch/buttons/Leds message
                value = int(self.RX_packet[1] & 0x7F) | int((self.RX_packet[0] & 0x01) << 7);
                # decode UNtouch/buttons/LEDs
                if (self.RX_packet[0] & 0x1E) == self.PICOMID_UNTOUCH:
                    GLib.idle_add(self.emit, 'fader_untouched', value)
                if (self.RX_packet[0] & 0x1E) == self.PICOMID_MUTE:
                    GLib.idle_add(self.emit, 'mute_button_changed', value)
                if  (self.RX_packet[0] & 0x1E) == self.PICOMID_SOLO:
                    GLib.idle_add(self.emit, 'solo_button_changed', value)
                if (self.RX_packet[0] & 0x1E) == self.PICOMID_REC:
                    GLib.idle_add(self.emit, 'rec_button_changed', value)
                if (self.RX_packet[0] & 0x1E) == self.PICOMID_SELECT:
                    GLib.idle_add(self.emit, 'sel_button_changed', value)

        self.RX_packet.clear()

    # Emit the signal to update buttons/LEDs
    def update_buttonLeds(self, value):
        print("Testing to update buttons/LEDs", value)  # TODO create the GObject signals
        # TODO this is just a simple example, button/LEDS must be decoded!
        return False

    def close(self):
        if self.serial_polling:
            self.serial_polling = False
            self.serial_read_thread.join()
        if self.ser.is_open:
            self.ser.close()

    def __del__(self):
        self.close()
