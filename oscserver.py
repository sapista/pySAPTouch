""" OSCServer Class
This class uses the liblo.ServerThread to receive osc messages in an independent thread.
When an OSC message is received, it is parsed and the correct function of OSCReceiveSignals called.
This models ensures a thread-safe gtk signal generation for incoming osc messages
"""

""" Example of OSC debuging using liblo send_osc and dump_osc
1. Open two terminals
2. In the receiver terminal: dump_osc 8000
3. In the send terminal: send_osc osc.udp://127.0.0.1:3819 /strip/list
"""

import stripselwidget
import liblo
import socket
from gi.repository import GObject


class OSCServer(GObject.GObject):
    __gsignals__ = {
        'list_reply_track': (GObject.SIGNAL_RUN_LAST, None,
                             (int, str, int,  # ssid, name, type
                              bool, bool, bool,  # mute, solo, rec
                              int, int)),  # inputs, outputs

        'list_reply_bus': (GObject.SIGNAL_RUN_LAST, None,
                           (int, str, int,  # ssid, name, type
                            bool, bool,  # mute, solo
                            int, int)),  # inputs, outputs

        'list_reply_end': (GObject.SIGNAL_RUN_LAST, None,
                           ()),

        'fader_changed': (GObject.SIGNAL_RUN_LAST, None,
                          (int, float)),

        'fader_gain_changed': (GObject.SIGNAL_RUN_LAST, None,
                          (int, float)),

        'solo_changed': (GObject.SIGNAL_RUN_LAST, None,
                         (int, bool)),

        'mute_changed': (GObject.SIGNAL_RUN_LAST, None,
                         (int, bool)),

        'rec_changed': (GObject.SIGNAL_RUN_LAST, None,
                        (int, bool)),

        'select_changed': (GObject.SIGNAL_RUN_LAST, None,
                           (int, bool)),

        'meter_changed': (GObject.SIGNAL_RUN_LAST, None,
                          (int, float)),

        'smpte_changed': (GObject.SIGNAL_RUN_LAST, None,
                          (str,)),

        'select_name_changed': (GObject.SIGNAL_RUN_LAST, None,
                          (str,)),

        'select_phase_changed': (GObject.SIGNAL_RUN_LAST, None,
                                (int,)),

        'select_rec_changed': (GObject.SIGNAL_RUN_LAST, None,
                                (int,)),

        'select_mute_changed': (GObject.SIGNAL_RUN_LAST, None,
                                (int,)),

        'select_solo_changed': (GObject.SIGNAL_RUN_LAST, None,
                                (int,)),

        'select_soloIso_changed': (GObject.SIGNAL_RUN_LAST, None,
                                    (int,)),

        'select_soloLock_changed': (GObject.SIGNAL_RUN_LAST, None,
                                    (int,)),

        'select_monitorIn_changed': (GObject.SIGNAL_RUN_LAST, None,
                                    (int,)),

        'select_monitorDisk_changed': (GObject.SIGNAL_RUN_LAST, None,
                                        (int,)),

        'select_ninputs_changed': (GObject.SIGNAL_RUN_LAST, None,
                                        (int,)),

        'select_noutputs_changed': (GObject.SIGNAL_RUN_LAST, None,
                                   (int,)),

        'select_trimdB_changed': (GObject.SIGNAL_RUN_LAST, None,
                                    (float,)),

        'select_fader_changed': (GObject.SIGNAL_RUN_LAST, None,
                                  (float,)),

        'select_fader_gain_changed': (GObject.SIGNAL_RUN_LAST, None,
                                 (float,)),

        'select_pan_pos_changed': (GObject.SIGNAL_RUN_LAST, None,
                                 (float,)),

        'select_pan_width_changed': (GObject.SIGNAL_RUN_LAST, None,
                                   (float,)),

        'select_trimdB_automation_changed': (GObject.SIGNAL_RUN_LAST, None,
                                     (int,)),

        'select_fader_automation_changed': (GObject.SIGNAL_RUN_LAST, None,
                                            (int,)),

        'select_send_name_changed': (GObject.SIGNAL_RUN_LAST, None,
                                            (int, str)),

        'select_send_enable_changed': (GObject.SIGNAL_RUN_LAST, None,
                                     (int, bool)),

        'select_send_fader_changed': (GObject.SIGNAL_RUN_LAST, None,
                                       (int, float)),

        'select_send_gain_changed': (GObject.SIGNAL_RUN_LAST, None,
                                      (int, float)),

        'send_reply_bus': (GObject.SIGNAL_RUN_LAST, None,
                           (int, str, int, )),  # origin ssid, target bus name, send ID

        'send_reply_end': (GObject.SIGNAL_RUN_LAST, None,
                           ()),

        'unknown_message': (GObject.SIGNAL_RUN_LAST, None,
                            (str,))

    }

    def __init__(self, osc_port):
        GObject.GObject.__init__(self)
        self.OSCReceiver = liblo.ServerThread(osc_port)

        #Increase the received socket buffer
        fd =  self.OSCReceiver.fileno()
        sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4194304) # 4 MB buffer

        # TODO this UDP buffer is going to be limited by OS!
        #To make this change permanent so it survives a reboot,
        # add the line net.core.rmem_max=4194304 to the bottom of the /etc/sysctl.conf file.

        self.OSCReceiver.add_method("/strip/fader", 'if', self.fader_callback)
        self.OSCReceiver.add_method("/strip/gain", 'if', self.fader_gain_callback)
        self.OSCReceiver.add_method("/strip/solo", 'if', self.solo_callback)
        self.OSCReceiver.add_method("/strip/mute", 'if', self.mute_callback)
        self.OSCReceiver.add_method("/strip/recenable", 'if', self.rec_callback)
        self.OSCReceiver.add_method("/strip/select", 'if', self.select_callback)
        self.OSCReceiver.add_method("/strip/meter", 'if', self.meter_callback)
        self.OSCReceiver.add_method("/reply", 'ssiiiiii', self.reply_callback_Track)
        self.OSCReceiver.add_method("/reply", 'ssiiiii', self.reply_callback_Bus)
        self.OSCReceiver.add_method("/reply", 'shhi', self.reply_callback_EndRoute)
        self.OSCReceiver.add_method("/position/smpte", 's', self.smpte_position_callback)
        self.OSCReceiver.add_method("/select/name", 's', self.select_name_callback)
        self.OSCReceiver.add_method("/select/polarity", 'i', self.select_phase_callback)
        self.OSCReceiver.add_method("/select/recenable", 'i', self.select_rec_callback)
        self.OSCReceiver.add_method("/select/mute", 'i', self.select_mute_callback)
        self.OSCReceiver.add_method("/select/solo", 'i', self.select_solo_callback)
        self.OSCReceiver.add_method("/select/solo_iso", 'i', self.select_soloIso_callback)
        self.OSCReceiver.add_method("/select/solo_safe", 'i', self.select_soloLock_callback)
        self.OSCReceiver.add_method("/select/monitor_input", 'i', self.select_monitorIn_callback)
        self.OSCReceiver.add_method("/select/monitor_disk", 'i', self.select_monitorDisk_callback)
        self.OSCReceiver.add_method("/select/n_inputs", 'i', self.select_ninputs_callback)
        self.OSCReceiver.add_method("/select/n_outputs", 'i', self.select_noutputs_callback)
        self.OSCReceiver.add_method("/select/trimdB", 'f', self.select_trimdB_callback)
        self.OSCReceiver.add_method("/select/fader", 'f', self.select_fader_callback)
        self.OSCReceiver.add_method("/select/gain", 'f', self.select_fader_gain_callback)
        self.OSCReceiver.add_method("/select/pan_stereo_position", 'f', self.select_pan_pos_callback)
        self.OSCReceiver.add_method("/select/pan_stereo_width", 'f', self.select_pan_width_callback)
        self.OSCReceiver.add_method("/select/trimdB/automation", 'i', self.select_trimdB_automation_callback)
        self.OSCReceiver.add_method("/select/fader/automation", 'i', self.select_fader_automation_callback)
        self.OSCReceiver.add_method("/select/send_name", 'is', self.select_send_name_callback)
        self.OSCReceiver.add_method("/select/send_fader", 'if', self.select_send_fader_callback)
        self.OSCReceiver.add_method("/select/send_gain", 'if', self.select_send_gain_callback)
        self.OSCReceiver.add_method("/select/send_enable", 'if', self.select_send_enable_callback)
        self.OSCReceiver.add_method("/strip/sends", None, self.sends_query_callback)

        #TODO add send callbacks
        self.OSCReceiver.add_method(None, None, self.fallback)

    def start(self):
        self.OSCReceiver.start()

    def stop(self):
        self.OSCReceiver.stop()

    def fader_callback(self, path, args):
        i, f = args
        GObject.idle_add(self.emit, 'fader_changed', i, f)

    def fader_gain_callback(self, path, args):
        i, f = args
        GObject.idle_add(self.emit, 'fader_gain_changed', i, f)

    def solo_callback(self, path, args):
        i, f = args
        GObject.idle_add(self.emit, 'solo_changed', i, f)

    def mute_callback(self, path, args):
        i, f = args
        GObject.idle_add(self.emit, 'mute_changed', i, f)

    def rec_callback(self, path, args):
        i, f = args
        GObject.idle_add(self.emit, 'rec_changed', i, f)

    def select_callback(self, path, args):
        i, f = args
        GObject.idle_add(self.emit, 'select_changed', i, f)

    def meter_callback(self, path, args):
        i, f = args
        GObject.idle_add(self.emit, 'meter_changed', i, f)

    def reply_callback_Track(self, path, args):
        sstriptype, sstripname, inumins, inumouts, imute, isolo, issid, irec = args
        GObject.idle_add(self.emit, 'list_reply_track',
                         issid, sstripname,
                         stripselwidget.StripEnum().map_ardour_type(sstriptype),
                         imute, isolo, irec, inumins, inumouts)

    def reply_callback_Bus(self, path, args):
        sstriptype, sstripname, inumins, inumouts, imute, isolo, issid = args
        GObject.idle_add(self.emit, 'list_reply_bus',
                         issid, sstripname,
                         stripselwidget.StripEnum().map_ardour_type(sstriptype),
                         imute, isolo, inumins, inumouts)

    def reply_callback_EndRoute(self, path, args):
        sendroute, framerate, lastframenum, monitorsection = args
        if sendroute == "end_route_list":
            GObject.idle_add(self.emit, 'list_reply_end')

    def smpte_position_callback(self, path, args):
        GObject.idle_add(self.emit, 'smpte_changed', args)

    def select_name_callback(self, path, args):
        GObject.idle_add(self.emit, 'select_name_changed', args[0])

    def select_phase_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_phase_changed', i)

    def select_rec_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_rec_changed', i)

    def select_mute_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_mute_changed', i)

    def select_solo_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_solo_changed', i)

    def select_soloIso_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_soloIso_changed', i)

    def select_soloLock_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_soloLock_changed', i)

    def select_monitorIn_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_monitorIn_changed', i)

    def select_monitorDisk_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_monitorDisk_changed', i)

    def select_ninputs_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_ninputs_changed', i)

    def select_noutputs_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_noutputs_changed', i)

    def select_trimdB_callback(self, path, args):
        i = float(args[0])
        GObject.idle_add(self.emit, 'select_trimdB_changed', i)

    def select_fader_callback(self, path, args):
        i = float(args[0])
        GObject.idle_add(self.emit, 'select_fader_changed', i)

    def select_fader_gain_callback(self, path, args):
        i = float(args[0])
        GObject.idle_add(self.emit, 'select_fader_gain_changed', i)

    def select_pan_pos_callback(self, path, args):
        i = float(args[0])
        GObject.idle_add(self.emit, 'select_pan_pos_changed', i)

    def select_pan_width_callback(self, path, args):
        i = float(args[0])
        GObject.idle_add(self.emit, 'select_pan_width_changed', i)

    def select_fader_automation_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_fader_automation_changed', i)

    def select_trimdB_automation_callback(self, path, args):
        i = int(args[0])
        GObject.idle_add(self.emit, 'select_trimdB_automation_changed', i)

    def select_send_name_callback(self, path, args):
        i, name = args
        GObject.idle_add(self.emit, 'select_send_name_changed', i, name)

    def select_send_fader_callback(self, path, args):
        i, f = args
        GObject.idle_add(self.emit, 'select_send_fader_changed', i, f)

    def select_send_gain_callback(self, path, args):
        i, f = args
        GObject.idle_add(self.emit, 'select_send_gain_changed', i, f)

    def select_send_enable_callback(self, path, args):
        i, b = args
        GObject.idle_add(self.emit, 'select_send_enable_changed', i, b)

    def sends_query_callback(self, path, args):
        strip_ssid = int(args[0]) #Get strip ssid
        for i in range(0, (len(args) - 1) // 5):
            bus_name = str(args[2 + (i * 5)])
            send_ID = int(args[3 + (i * 5)])
            GObject.idle_add(self.emit, 'send_reply_bus', strip_ssid, bus_name, send_ID)
        GObject.idle_add(self.emit, 'send_reply_end')

    def fallback(self, path, args, types, src):
        str_types = ""
        str_args = ""
        for a, t in zip(args, types):
            str_types = str_types + "%s" % t
            str_args = str_args + "'%s'" % a + " "
        GObject.idle_add(self.emit, 'unknown_message', ("received unknown message: %s " % path) + str_types + " " + str_args)
