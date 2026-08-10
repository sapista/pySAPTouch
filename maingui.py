#!/usr/bin/env python

import gi

from stripTypes import StripEnum

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

#import liblo
import pyliblo3 as liblo
import sys
import oscserver
import stripselwidget
import stripctlwidget
import simplebuttonwidget
import math
import xml.etree.ElementTree as ET
import ast
import customframewidget
import bankAvrController
import selectFaderCtlWidget
import stripTable
import stripTypes
import time
import oscconnectionwatchdog
import LEDWidget

""" ControllerGUI class
This class implements a gtk GUI for sending osc messages using the liblo.send() method.
The GUI is also able to receive OSC messages in a signal-handler model using OSCServer class.
"""


class ControllerGUI(Gtk.Window):
    def delete_event(self, widget, event, data=None):
        quitDialog = Gtk.MessageDialog(parent=widget,
                                       modal=True,
                                       message_type=Gtk.MessageType.QUESTION,
                                       buttons=Gtk.ButtonsType.YES_NO,
                                       text="Are you sure to quit?")

        # Handle response asynchronously instead of blocking with .run()
        quitDialog.connect("response", self._on_quit_response)
        quitDialog.show_all()
        return True

    def _on_quit_response(self, dialog, response_id):
        dialog.destroy()

        if response_id == Gtk.ResponseType.YES:
            self.watchdog.stop()
            self.oscserver.stop()
            self.faderCtl.close()
            self.destroy(None)

    def destroy(self, widget):
        #Defers main_quit to the next idle loop cycle for a clean exit
        GLib.idle_add(Gtk.main_quit)

    def btn_close_clicked(self, widget):
        self.close()

    def btn_session_save_clicked(self, widget):
        liblo.send(self.target, "/save_state")

    def btn_smart_mode_clicked(self, widget):
        liblo.send(self.target, "/access_action/MouseMode/set-mouse-mode-object-range")

    def btn_object_mode_clicked(self, widget):
        liblo.send(self.target, "/access_action/MouseMode/set-mouse-mode-object")

    def btn_range_mode_clicked(self, widget):
        liblo.send(self.target, "/access_action/MouseMode/set-mouse-mode-range")

    def btn_cut_mode_clicked(self, widget):
        liblo.send(self.target, "/access_action/MouseMode/set-mouse-mode-cut")

    def btn_timefx_mode_clicked(self, widget):
        liblo.send(self.target, "/access_action/MouseMode/set-mouse-mode-timefx")

    def btn_draw_mode_clicked(self, widget):
        liblo.send(self.target, "/access_action/MouseMode/set-mouse-mode-draw")

    def btn_content_mode_clicked(self, widget):
        liblo.send(self.target, "/access_action/MouseMode/set-mouse-mode-content")

    def btn_metronome_clicked(self, widget):
        liblo.send(self.target, "/toggle_click")

    def btn_solo_cancel_clicked(self, widget):
        liblo.send(self.target, "/cancel_all_solos", 1.0)

    def btn_playStop_clicked(self, widget):
        liblo.send(self.target, "/toggle_roll")

    def btn_loop_clicked(self, widget):
        liblo.send(self.target, "/loop_toggle")
        if self.bLooping:
            self.bLooping = False
            self.btn_loop.set_image(self.btn_loop_WhiteIcon)
        else:
            self.bLooping = True

    def on_jog_mode_changed(self, widget):
        jog_id = -1
        self.btn_jog_mode.set_active_state(False)
        self.btn_scrub_mode.set_active_state(False)
        self.btn_scroll_mode.set_active_state(False)
        self.btn_marker_mode.set_active_state(False)
        self.btn_rgain_mode.set_active_state(False)
        if widget == self.btn_jog_mode:
            self.jog_mode = "Jog"
            jog_id = 0
            self.btn_jog_mode.set_active_state(True)
        elif widget == self.btn_scrub_mode:
            self.jog_mode = "Scrub"
            self.btn_scrub_mode.set_active_state(True)
        elif widget == self.btn_scroll_mode:
            self.jog_mode = "Scroll"
            jog_id = 5
            self.btn_scroll_mode.set_active_state(True)
        elif widget == self.btn_marker_mode:
            self.jog_mode = "Marker"
            jog_id = 4
            self.btn_marker_mode.set_active_state(True)
        elif widget == self.btn_rgain_mode:
            self.jog_mode = "R.Gain"
            self.btn_rgain_mode.set_active_state(True)

        if jog_id != -1:
            liblo.send(self.target, "/jog/mode", jog_id)
            liblo.send(self.target, "/transport_stop")

    def on_encoder_incremented(self, event, value):
        if self.encoder_reverse: value = -value

        #Measure time elapsed between encoder ticks
        encoder_current_time = time.monotonic()
        encoder_elapsed = (encoder_current_time - self.encoder_last_time)
        self.encoder_last_time = encoder_current_time

        #Calculate encoder speed ( a.k.a. tick rate)
        encoder_current_speed = value / encoder_elapsed # Ticks/Second

        #Do not allow to fast speed changes, some dynamics
        self.encoder_speed = 0.6*self.encoder_speed + 0.4*encoder_current_speed

         #Limit speed:
        if self.encoder_speed  > 100: self.encoder_speed  = 100
        if self.encoder_speed  < -100: self.encoder_speed  = -100

        #print(f"DBG Enc: '{value}' elapsed: '{encoder_elapsed}' tick_rate_CURR: '{encoder_current_speed}' tick_rate_AVG: '{self.encoder_speed}'")
        #return

        if self.jog_mode == "Jog":
            liblo.send(self.target, "/jog", self.encoder_speed * self.encoder_accel)

        elif self.jog_mode == "Scrub":
            tspeed =  self.encoder_speed * self.encoder_accel * 1.5
            if tspeed < 0.4 and tspeed > 0: tspeed = 0.4
            if tspeed > -0.4 and tspeed < 0: tspeed = -0.4
            if tspeed > 1.0: tspeed = 1.0
            if tspeed < -1.0: tspeed = -1.0
            self.send_throttled_speed(tspeed)

            # Cancel the existing GTK timer if the wheel is still spinning
            if self.JogWheel_timer_id is not None:
                GLib.source_remove(self.JogWheel_timer_id)
                self.JogWheel_timer_id = None

            # Schedule encoder_send_jog_stop to trigger after encoder inactivity
            self.JogWheel_timer_id = GLib.timeout_add(300, self.encoder_send_jog_stop)

        elif self.jog_mode == "Scroll":
            liblo.send(self.target, "/jog", self.encoder_speed * self.encoder_accel)

        elif self.jog_mode == "Marker":
            self.encoder_ticks_marker_counter = self.encoder_ticks_marker_counter + value

            if self.encoder_ticks_marker_counter >= self.encoder_ticks_for_marker:
                liblo.send(self.target, "/jog", 1)
                self.encoder_ticks_marker_counter = 0

            if self.encoder_ticks_marker_counter <= -self.encoder_ticks_for_marker:
                liblo.send(self.target, "/jog", -1)
                self.encoder_ticks_marker_counter = 0

        elif self.jog_mode == "R.Gain":
            if value > 0:
                liblo.send(self.target, "/access_action/Region/boost-region-gain")
            else:
                liblo.send(self.target, "/access_action/Region/cut-region-gain")

    def encoder_send_jog_stop(self):
        liblo.send(self.target, "/transport_stop")
        self.JogWheel_timer_id = None
        self.encoder_speed = 0.0
        self.last_encoder_speed_time = time.monotonic() #Avoid sending other OSC speed commands to soon
        return False  # Return False so GTK knows to run this callback ONLY ONCE

    def send_throttled_speed(self, speed):
        current_time = time.monotonic()
        if (current_time - self.last_encoder_speed_time >= 0.020):
            liblo.send(self.target, "/set_transport_speed", speed)
            self.last_encoder_speed_time = current_time

    def fader_bank_mode_changed(self, event, channel, value):
        if self.strip_table.get_number_of_strips() > 0:  # Only if we have strip list from DAW
            selSSID = self.strips_list_selbank[channel].get_ssid()
            if selSSID is not None:
                #TODO testing new method
                self.osc_send2ssid("/strip/fader/touch", selSSID, 1)
                self.osc_send2ssid("/strip/fader", selSSID, value)
                #liblo.send(self.target, "/strip/fader/touch", selSSID, 1)  # Using floats it works
                #liblo.send(self.target, "/strip/fader", selSSID, value)
        return True

    def fader_bank_mode_untouched(self, event, value):
        if self.strip_table.get_number_of_strips() > 0:  # Only if we have strip list from DAW
            # print("Unotuch event: %x", value)
            for i in range(0, 8):
                if value & (1 << i):
                    selSSID = self.strips_list_selbank[i].get_ssid()
                    if selSSID is not None:
                        # TODO testing new method
                        self.osc_send2ssid("/strip/fader/touch", selSSID, 0)
                        #liblo.send(self.target, "/strip/fader/touch", selSSID, 0)
        return True

    def trim_single_mode_changed(self, event, value):
        # TODO testing new method
        self.osc_send2select("/select/trimdB/touch", 1)
        self.osc_send2select("/select/trimdB", value)
        #liblo.send(self.target, "/select/trimdB/touch", 1)
        #liblo.send(self.target, "/select/trimdB", value)
        return True

    def trim_single_mode_untouched(self, event):
        # TODO testing new method
        self.osc_send2select("/select/trimdB/touch", 1)
        #liblo.send(self.target, "/select/trimdB/touch", 0)
        return True

    def fader_single_mode_changed(self, event, value):
        # TODO testing new method
        self.osc_send2select("/select/fader/touch", 1)
        self.osc_send2select("/select/fader", value)
        #liblo.send(self.target, "/select/fader/touch", 1)
        #liblo.send(self.target, "/select/fader", value)
        return True

    def fader_single_mode_untouched(self, event):
        # TODO testing new method
        self.osc_send2select("/select/fader/touch", 0)
        #liblo.send(self.target, "/select/fader/touch", 0)
        return True

    def pan_pos_single_mode_changed(self, event, value):
        # TODO enable touch automation when available in Ardour
        # self.osc_send2select("/select/pan_stereo_position/touch", 1)

        # Make the fader sticky to the center point (0.5)
        corrected_pan_val = value
        dist_2_center = abs(corrected_pan_val - 0.5)
        if dist_2_center < 0.05:
            corrected_pan_val = 0.5

        self.osc_send2select("/select/pan_stereo_position", corrected_pan_val)

        return True

    def pan_pos_single_mode_untouched(self, event):
        # TODO enable touch automation when available in Ardour
        # self.osc_send2select("/select/pan_stereo_position/touch", 0)
        return True

    def pan_width_single_mode_changed(self, event, value):
        if self.ePanner.get_panner_has_width_control():
            # TODO enable touch automation when available in Ardour
            # self.osc_send2select( "/select/pan_stereo_width/touch", 1)

            #Prefer center point (0.5)
            corrected_pan_val = value
            dist_2_center = abs(corrected_pan_val - 0.5)
            if dist_2_center < 0.05:
                corrected_pan_val = 0.5

            #TODO I believe this is an ardour bug but pan must be sent between -1 and 1
            corrected_pan_val = corrected_pan_val * 2.0 - 1.0

            self.osc_send2select( "/select/pan_stereo_width", corrected_pan_val)
        return True

    def pan_width_single_mode_untouched(self, event):
        #if self.ePanner.get_panner_has_width_control():
            # TODO enable touch automation when available in Ardour
            # self.osc_send2select("/select/pan_stereo_width/touch", 0)
        return True

    def send_single_mode_changed(self, event, channel, value):
        if self.sends_table.get_number_of_strips() > 0:  # Only if we have strip list from DAW
            selSSID = self.eSendsCtl[channel].get_sendID()
            if selSSID is not None:
                # TODO enable touch automation when available in Ardour (Unhandled OSC message: /select/send/touch i:3 i:1)
                #self.osc_send2ssid( "/select/send/touch", selSSID, 1)
                self.osc_send2ssid( "/select/send_fader", selSSID, value)
            else:
                #Restore fader to zero
                self.faderCtl.move_single_send(channel, 0.0)
        return True

    def send_single_mode_untouched(self, event, channel):
        selSSID = self.eSendsCtl[channel].get_sendID()
        # TODO enable touch automation when available in Ardour (Unhandled OSC message: /select/send/touch i:3 i:1)
        #if selSSID is not None:
            #self.osc_send2ssid( "/select/send/touch", selSSID, 0)
        return True

    def strip_select_changed(self, widget, issid):
        self.safe_strip_select(issid)

    def refresh_strip_list_ALL(self, widget):
        self.bOSC_is_ready = False
        # Config the surface as infinite banks, track setting, strip feedback and fader as position values
        #liblo.send(self.target, "/set_surface", 0, 23, 24779, 2, 0)  # Check Ardour OSC preferences for reference of these values

        liblo.send(self.target, "/set_surface", 0, 7, 24779, 2, 0)  # Check Ardour OSC preferences for reference of these values
        # the feedback value of 24771 includes the level meters as text and the changes the #reply messages to /reply

        self.send_osc_refresh_strip_list()

    def btn_VCA_mode_clicked(self, widget):
        if self.bVCAmode is not True:
            self.bOSC_is_ready = False
            self.strip_table.set_vca_mode(True)
            self.bSpill = False
            self.bVCAmode = True
            self.btn_activate_VCA_mode.set_active_state(True)
            self.btn_activate_TrkBus_mode.set_active_state(False)

            liblo.send(self.target, "/set_surface/strip_types", 16)
            self.send_osc_refresh_strip_list()

    def btn_TrkBus_mode_clicked(self, widget):
        if self.bVCAmode is True or self.bSpill is True:
            self.bOSC_is_ready = False
            self.strip_table.set_vca_mode(False)
            self.bSpill = False
            self.bVCAmode = False
            self.btn_activate_VCA_mode.set_active_state(False)
            self.btn_activate_TrkBus_mode.set_active_state(True)

            liblo.send(self.target, "/set_surface/strip_types", 7)
            self.send_osc_refresh_strip_list()

    def bank_channel_select_changed(self, widget, index, value):
        self.strips_list_selbank[index].set_select(value)

    def bank_channel_ssid_name_changed(self, widget, index, ssid, name):
        self.strips_list_selbank[index].set_ssid_name(ssid, name)

    def bank_channel_type_changed(self, widget, index, type):
        self.strips_list_selbank[index].set_strip_type(type)
        if type is StripEnum.VCA and self.bSpill:
            self.strips_list_selbank[index].btn_spill.hide()

    def bank_channel_fader_changed(self, widget, index, value):
        self.faderCtl.move_bank_fader(index, value)

    def bank_channel_fader_gain_changed(self, widget, index, value):
        self.strips_list_selbank[index].set_gain_label(value)

    def bank_channel_solo_changed(self, widget, index, value):
        self.strips_list_selbank[index].set_solo(value)

    def bank_channel_mute_changed(self, widget, index, value):
        self.strips_list_selbank[index].set_mute(value)

    def bank_channel_rec_changed(self, widget, index, value):
        self.strips_list_selbank[index].set_rec(value)

    # Callback of current bank controls
    def bank_edit_clicked (self, widget, ichannel):
        self.safe_strip_select(ichannel)
        self.faderCtl.set_state(bankAvrController.FaderBankState.SINGLE_CHANNEL_EDIT)
        self.stack.set_visible_child_full("edit_mode", Gtk.StackTransitionType.SLIDE_UP) #Switch to edit mode
        #Hide Stripe/VCA buttons to avoid potential confusion and force to use the close button X
        self.btn_activate_VCA_mode.hide()
        self.btn_activate_TrkBus_mode.hide()

    def bank_sel_clicked(self, widget, ichannel, bvalue):
        if bvalue:
            self.safe_strip_select(ichannel)

    def bank_rec_clicked(self, widget, ichannel, bvalue):
        liblo.send(self.target, "/strip/recenable", ichannel, int(bvalue))

    def bank_spill_clicked(self, widget, ichannel):
        self.bOSC_is_ready = False
        self.strip_table.set_vca_mode(False)
        self.bSpill = True
        self.bVCAmode = False
        self.btn_activate_VCA_mode.set_active_state(False)
        self.btn_activate_TrkBus_mode.set_active_state(True)

        liblo.send(self.target, "/strip/spill", ichannel)
        self.send_osc_refresh_strip_list()

    def bank_mute_clicked(self, widget, ichannel, bvalue):
        liblo.send(self.target, "/strip/mute", ichannel, int(bvalue))

    def bank_solo_clicked(self, widget, ichannel, bvalue):
        liblo.send(self.target, "/strip/solo", ichannel, int(bvalue))

    # Callbacks from OSC incoming messages
    def fader_osc_changed(self, widget, ichannel, fvalue):
        #print("fader received on channel '%d' with value '%f'" % (ichannel, fvalue))
        self.strip_table.set_fader(ichannel, fvalue)

    def fader_gain_osc_changed(self, widget, ichannel, fvalue):
        #print("fader received on channel '%d' with value '%f'" % (ichannel, fvalue))
        self.strip_table.set_fader_gain(ichannel, fvalue)

    def solo_osc_changed(self, widget, ichannel, bvalue):
        # print "solo received on channel '%d' with state '%s'" % (ichannel, bvalue)
        self.strip_table.set_solo(ichannel, bvalue)

    def mute_osc_changed(self, widget, ichannel, bvalue):
        # print "mute received on channel '%d' with state '%s'" % (ichannel, bvalue)
        self.strip_table.set_mute(ichannel, bvalue)

    def rec_osc_changed(self, widget, ichannel, bvalue):
        # print "rec received on channel '%d' with state '%s'" % (ichannel, bvalue)
        self.strip_table.set_rec(ichannel, bvalue)

    def select_osc_changed(self, widget, ichannel, bvalue):
        #print( "select received on channel '%d' with state '%s'" % (ichannel, bvalue))
        if not self.bVCAmode:
            self.strip_table.strip_select(ichannel, bvalue) #This is ok for track/bus since ssid is checked inside

            if bvalue:

                self.eLbl_ssid.set_markup("<span weight='bold' size='xx-large' color='white'>("+str(ichannel)+")</span>")

                # Query sends, instead of quering just hide all strips and let each send command to show its strip
                for i in range(0, self.sends_table.get_number_of_strips()):
                    self.sends_table.hide_strip(i + 1)
                    self.sends_table.set_strip_name(self.sends_table.get_strip_ssid(i), "") #Using empty name to hide unused sends

                self.sends_table.strip_select(1,True) #Ensuer to start always selecting the first bank

        if bvalue:
            self.iLastSelectedTrackBus_ssid = ichannel

    def meter_osc_changed(self, widget, ichannel, fvalue):
        # print ("meter on channel '%d' = '%s'" % (ichannel, fvalue))
        self.strip_table.set_meter(ichannel, fvalue)

    def smpte_osc_changed(self, widget, svalue):
        # print("SMPTE '%s'" % (svalue))
        self.btn_playpause.set_image(self.btn_playpause_GreenIcon)
        if self.bLooping:
            self.btn_loop.set_image(self.btn_loop_GreenIcon)
        GLib.source_remove(self.smpte_timer_ID)  # Destroy previous timmer if running
        self.smpte_timer_ID = GLib.timeout_add(200, self.smpte_timeout)  # Reset timmer

    def unknown_osc_message(self, widget, svalue):
        print(svalue)

    def smpte_timeout(self):
        self.btn_playpause.set_image(self.btn_playpause_WhiteIcon)
        self.btn_loop.set_image(self.btn_loop_WhiteIcon)
        return True

    def list_osc_reply_track(self, widget, ssid, name, type, mute, solo, rec, inputs, outputs):
        self.strip_table.register_strip(ssid, name, type, mute, solo, rec, inputs, outputs)

    def list_osc_reply_bus(self, widget, ssid, name, type, mute, solo, inputs, outputs):
        self.strip_table.register_strip(ssid, name, type, mute, solo, None, inputs, outputs)

    def list_osc_reply_end(self, widget):
        #Connected, set watchdog
        self.watchdog.set_OSC_online(True)
        self.LED_OSCconnection.set_value(True)
        self.LED_OSCconnection.set_label("OSC Online")
        self.bOSC_is_ready = True

        if self.bVCAmode:
            #VCA MODE
            self.strip_table.reset_current_selected_bank()
            if self.strip_table.get_number_of_strips() > 0:
                self.safe_strip_select(self.strip_table.get_strip_ssid(0))

        else:
            #TRACK/BUS MODE
            if self.strip_table.get_number_of_strips() > 0:
                if self.iLastSelectedTrackBus_ssid is None:
                    self.safe_strip_select(self.strip_table.get_strip_ssid(0))
                else:
                    self.safe_strip_select(self.iLastSelectedTrackBus_ssid)

        if self.bSpill:
            if self.strip_table.get_number_of_strips() > 1:
                self.safe_strip_select(self.strip_table.get_strip_ssid(0)) #In VCA spill mode select always the first stripe
                GLib.timeout_add(400, self.spill_mode_blink_timer)
            else:
                #Show a message to inform there is no Strip assigned to this VCA
                dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    modal=True,
                    destroy_with_parent=True,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.CLOSE,
                    text="There is no strip assigned to the spilled VCA"
                )
                dialog.set_title("VCA Error")
                dialog.run()
                dialog.destroy()

                #Return to VCA mode
                self.bVCAmode = False
                self.btn_VCA_mode_clicked(None)

    #Event from Ardour, strip list changed (added or removed track/bus)
    def list_osc_changed(self, widget):
        if self.strip_table.get_number_of_strips() == 0:
            return #Avoid doing anything if my table is empty

        print("DBG: Strip list changed event!")
        #TODO its refresehn non stop! each time a track is selected ardour sends it! pffff
        #Refresh current strip list
        #self.send_osc_refresh_strip_list()

    def send_osc_refresh_strip_list(self):
        self.strip_table.clear_strips()
        GLib.timeout_add(200, self.osc_exec_list) #delay the /list command to give ardour time to process the /set_surface

    def osc_exec_list(self):
        liblo.send(self.target, "/strip/list")
        return False

    #Edit Mode button signals
    def eBtn_close_clicked(self, widget):
        self.faderCtl.set_state(bankAvrController.FaderBankState.EIGHT_CHANNELS_FADERS)
        self.stack.set_visible_child_full("strip_list", Gtk.StackTransitionType.SLIDE_DOWN)
        self.btn_activate_VCA_mode.show()
        self.btn_activate_TrkBus_mode.show()

    def eBtn_next_clicked(self, widget):
        if self.strip_table.get_current_selected_strip_index() != None:
            next_select = self.strip_table.get_current_selected_strip_index() + 1
            if next_select == self.strip_table.get_number_of_strips():
                next_select = 0

            self.safe_strip_select(self.strip_table.get_strip_ssid(next_select))

    def eBtn_prev_clicked(self, widget):
        if self.strip_table.get_current_selected_strip_index() != None:
            next_select = self.strip_table.get_current_selected_strip_index() - 1
            if next_select == -1:
                next_select = self.strip_table.get_number_of_strips() - 1

            self.safe_strip_select(self.strip_table.get_strip_ssid(next_select))

    def edit_phaseBtn_clicked(self, widget):
        liblo.send(self.target, "/select/polarity", int(not self.eBtn_phase.get_active_state()))

    def edit_recBtn_clicked(self, widget):
        liblo.send(self.target, "/select/recenable", int(not self.eBtn_rec.get_active_state()))

    def edit_muteBtn_clicked(self, widget):
        liblo.send(self.target, "/select/mute", int(not self.eBtn_mute.get_active_state()))

    def edit_soloBtn_clicked(self, widget):
        liblo.send(self.target, "/select/solo", int(not self.eBtn_solo.get_active_state()))

    def edit_soloIsoBtn_clicked(self, widget):
        liblo.send(self.target, "/select/solo_iso", int(not self.eBtn_soloIso.get_active_state()))

    def eBtn_soloLock_clicked(self, widget):
        liblo.send(self.target, "/select/solo_safe", int(not self.eBtn_soloLock.get_active_state()))

    def eBtn_monIn_clicked(self, widget):
        liblo.send(self.target, "/select/monitor_input", int(not self.eBtn_monitorIn.get_active_state()))

    def eBtn_monDisk_clicked(self, widget):
        liblo.send(self.target, "/select/monitor_disk", int(not self.eBtn_monitorDisk.get_active_state()))

    def edit_trimdB_automation_changed(self, widget, value):
        liblo.send(self.target, "/select/trimdB/automation", value)

    def edit_fader_automation_changed(self, widget, value):
        liblo.send(self.target, "/select/fader/automation", value)

    def edit_panner_automation_changed(self, widget, value):
        liblo.send(self.target, "/select/pan_stereo_position/automation", value)
        liblo.send(self.target, "/select/pan_stereo_width/automation", value)

    def edit_send_active_changed(self, widget, sendID, value):
        liblo.send(self.target, "/select/send_enable", sendID, int(value))

    #OSC receive commands for the edit mode
    def select_name_osc_changed(self, widget, value):
        self.eLbl_title.set_markup("<span weight='bold' size='xx-large' color='white'>" + value + "</span>")

    def select_phase_osc_changed(self, widget, value):
        self.eBtn_phase.set_active_state(bool(value))

    def select_rec_osc_changed(self, widget, value):
        self.eBtn_rec.set_active_state(bool(value))

    def select_mute_osc_changed(self, widget, value):
        self.eBtn_mute.set_active_state(bool(value))

    def select_solo_osc_changed(self, widget, value):
        self.eBtn_solo.set_active_state(bool(value))

    def select_soloIso_osc_changed(self, widget, value):
        self.eBtn_soloIso.set_active_state(bool(value))

    def select_soloLock_osc_changed(self, widget, value):
        self.eBtn_soloLock.set_active_state(bool(value))

    def select_monitorIn_osc_changed(self, widget, value):
        self.eBtn_monitorIn.set_active_state(bool(value))

    def select_monitorDisk_osc_changed(self, widget, value):
        self.eBtn_monitorDisk.set_active_state(bool(value))

    def select_nInputs_osc_changed(self, widget, value):
        self.eLbl_ins.set_text("In: " + str(value))

    def select_nOutputs_osc_changed(self, widget, value):
        self.eLbl_outs.set_text("Out: " + str(value))

    def select_trimdB_osc_changed(self, widget, value):
        self.faderCtl.move_single_trim(value)
        self.eTrimCtl.set_gain_label(value)

    def select_fader_osc_changed(self, widget, value):
        self.faderCtl.move_single_fader(value)

    def select_fader_gain_osc_changed(self, widget, value):
        self.eFaderCtl.set_gain_label(value)

    def select_panPos_osc_changed(self, widget, value):
        self.faderCtl.move_single_pan_pos(value)
        self.ePanner.set_panner_position(value)

    def select_panWidth_osc_changed(self, widget, value):
        #print("Pan Width received value '%f'" % (value))
        self.faderCtl.move_single_pan_width(value)
        self.ePanner.set_panner_width(value)

    def select_panner_width_control_osc_changed(self, widget, value):
        self.ePanner.set_panner_has_width_control(value)
        if not value:
            self.faderCtl.move_single_pan_width(0) #Force fader to zero to disable width control

    def select_trimdB_automation_osc_changed(self, widget, value):
        self.eTrimCtl.set_automation_mode(value)

    def select_fader_automation_osc_changed(self, widget, value):
        self.eFaderCtl.set_automation_mode(value)

    def select_pan_position_automation_osc_changed(self, widget, value):
        self.ePanner.set_automation_mode(value)

    def select_pan_width_automation_osc_changed(self, widget, value):
        #I prepared the signal but automation is linked in Ardour 8.12 to the position...
        # so I only have a single set of automation mode buttons for the whole panner widget
        self.ePanner.set_automation_mode(value)

    def select_send_name_osc_changed(self, widget, send_id, send_name):
        self.sends_table.set_strip_name(send_id, send_name)
        self.sends_table.show_strip(send_id)

    def strip_name_osc_changed(self, widget, ssid, name):
        if self.strip_table.get_number_of_strips() == 0:
            return

        # We do not know its just a name chance of a track or a strip re-arrangement, so better to refresh all
        #self.send_osc_refresh_strip_list()

        #TODO all commented out this may be the bug!
        """  
        #TODO think about this...
        curr_name = self.strip_table.get_strip_name(ssid)
        if curr_name is None:
            #Strip added so refresh the list
            self.send_osc_refresh_strip_list()
        else:
            # print("strip_name_osc_changed ssid '%d'  name '%s'" % (ssid, name))
            self.strip_table.set_strip_name(ssid, name)
        """

    def osc_heartbeat_tick(self, widget):
        if not self.watchdog.get_OSC_online():
            return
        self.watchdog.reset()
        self.LED_OSCconnection.set_value(not self.LED_OSCconnection.get_value())

    def on_watchdog_expired(self):
        if self.watchdog.get_OSC_online():
            #OSC connection lost! change to offline mode
            self.watchdog.set_OSC_online(False)
            self.LED_OSCconnection.set_value(False)
            self.LED_OSCconnection.set_label("OSC Offline")

        #print("Watchdog timed out! Connection lost. Reconnecting...")
        self.refresh_strip_list_ALL(None)
        self.watchdog.start()

    def osc_send2ssid(self, command, ssid, value):
        if self.bOSC_is_ready and self.strip_table.check_if_ssid_exists(ssid):
            liblo.send(self.target, command, ssid, value)

    def osc_send2select(self, command, value):
        if self.bOSC_is_ready:
            liblo.send(self.target, command, value)

    def select_send_enable_osc_changed(self, widget, send_id, send_enabled):
        self.sends_table.set_mute(send_id, send_enabled)

    def select_send_fader_osc_changed(self, widget, send_id, fader_value):
        self.sends_table.set_fader(send_id, fader_value)

    def select_send_gain_osc_changed(self, widget, send_id, gain_value):
        self.sends_table.set_fader_gain(send_id, gain_value)

    def send_select_changed(self, widget, issid):
        self.sends_table.strip_select(issid, True)  # This is ok for track/bus since ssid is checked inside

    def bank_send_active_changed(self, widget, index, value):
        self.eSendsCtl[index].set_send_active(value)

    def bank_send_fader_changed(self, widget, index, value):
        self.faderCtl.move_single_send(index, value)

    def bank_send_fader_gain_changed(self, widget, index, value):
        self.eSendsCtl[index].set_gain_label(value)

    def bank_send_ssid_name_changed(self, widget, index, ssid, name):
        if name == "": #Using empty name to hide unused sends
            self.eSendsCtl[index].hide()
            self.eSendsCtl[index].set_sendID(None)
            self.faderCtl.move_single_send(index, 0.0)
        else:
            self.eSendsCtl[index].show()
            self.eSendsCtl[index].set_sendID(ssid)
            self.eSendsCtl[index].set_name_label(name)

    #Safe select to handle state of stereo panners properly and unificate all calls to /strip/select
    def safe_strip_select(self, ssid):
        if self.strip_table.check_if_ssid_exists(ssid):
            if self.bVCAmode:
                self.strip_table.strip_select(ssid, True)  # This is ok for track/bus since ssid is checked inside
            else:
                liblo.send(self.target, "/strip/select", ssid, 0) #TODO I must send a zero not a 1 to select! this must be a bug in Ardour (8.12)!

    def spill_mode_blink_timer(self):
        if self.bSpill:
            self.btn_activate_TrkBus_mode.set_active_state(not self.btn_activate_TrkBus_mode.get_active_state())
            self.btn_activate_TrkBus_mode.set_label("SPILLED\nSTRIPS")
            self.btn_activate_VCA_mode.set_active_state(self.btn_activate_TrkBus_mode.get_active_state())
            self.btn_activate_VCA_mode.set_label("SPILLED\nVCA")
        else:
            self.btn_activate_TrkBus_mode.set_label("STRIPS")
            self.btn_activate_VCA_mode.set_label("VCA's")
        return self.bSpill

    def __init__(self):
        self.bOSC_is_ready = False #Block OSC sending if not ready and fully configured
        self.bVCAmode = False #Controls if its showing track/bus or VCA's
        self.bSpill = False #Signal when in spill mode
        self.iLastSelectedTrackBus_ssid = None

        Gtk.Window.__init__(self, title="OSC Controller")
        # Reding config data from config.xml
        tree = ET.parse('config.xml')
        root = tree.getroot()

        osc_net = root.find('osc_net')
        daw_IP = osc_net.find('daw_ip').text
        daw_port = int(osc_net.find('daw_port').text)
        recv_port = int(osc_net.find('recv_port').text)

        avr_com = root.find('avr_com')
        serial_port = avr_com.find('serial_port').text
        baudrate = int(avr_com.find('baudrate').text)
        FADER_MIN = int(avr_com.find('fader_min').text)
        FADER_MAX = int(avr_com.find('fader_max').text)

        misc = root.find('misc')
        window_width = int(misc.find('window_width').text)
        window_height = int(misc.find('window_height').text)
        window_maximize = ast.literal_eval(misc.find('window_maximize').text)
        self.PIXELS_X_SECOND = int(misc.find('meter_waveform_speed').text)

        debug = root.find('debug')
        log_invalid_messages = ast.literal_eval(debug.find('log_invalid_messages').text)

        try:
            self.oscserver = oscserver.OSCServer(recv_port)
        except liblo.ServerError as err:
            print(str(err))
            sys.exit()

        try:
            self.target = liblo.Address(daw_IP, daw_port)
        except liblo.AddressError as err:
            print(str(err))
            sys.exit()

        self.vbox_top = Gtk.VBox()

        # Build the header bar
        self.headerBar = Gtk.HeaderBar()
        self.headerBar.set_show_close_button(False)
        self.set_titlebar(self.headerBar)
        self.ImgLogo = Gtk.Image.new_from_file("icons/sapaudio_logo.png")
        self.headerBar.set_title("SAPTouch")
        self.headerBar.set_custom_title(Gtk.Box()) #Remove title from the GUI (the logo will do)
        self.headerBar.pack_start(self.ImgLogo)

        self.hbox_top = Gtk.HBox()
        self.vbox_top.pack_start(self.hbox_top, expand=False, fill=False, padding=0)

        #Edit Mode buttons
        self.btn_smart_mode = Gtk.Button.new_with_label("")
        self.btn_smart_mode.get_child().set_markup("<span weight='bold' size='large' color='white'>Smart</span>")
        self.btn_smart_mode.connect("clicked", self.btn_smart_mode_clicked)
        self.hbox_top.pack_start(self.btn_smart_mode, expand=False, fill=False, padding=0)

        self.btn_object_mode = Gtk.Button()
        self.btn_object_mode.set_image(Gtk.Image.new_from_file("icons/object_mode.png"))
        self.btn_object_mode.connect("clicked", self.btn_object_mode_clicked)
        self.hbox_top.pack_start(self.btn_object_mode, expand=False, fill=False, padding=0)

        self.btn_range_mode = Gtk.Button()
        self.btn_range_mode.set_image(Gtk.Image.new_from_file("icons/range_mode.png"))
        self.btn_range_mode.connect("clicked", self.btn_range_mode_clicked)
        self.hbox_top.pack_start(self.btn_range_mode, expand=False, fill=False, padding=0)

        self.btn_cut_mode = Gtk.Button()
        self.btn_cut_mode.set_image(Gtk.Image.new_from_file("icons/cut_mode.png"))
        self.btn_cut_mode.connect("clicked", self.btn_cut_mode_clicked)
        self.hbox_top.pack_start(self.btn_cut_mode, expand=False, fill=False, padding=0)

        self.btn_timefx_mode = Gtk.Button()
        self.btn_timefx_mode.set_image(Gtk.Image.new_from_file("icons/timefx_mode.png"))
        self.btn_timefx_mode.connect("clicked", self.btn_timefx_mode_clicked)
        self.hbox_top.pack_start(self.btn_timefx_mode, expand=False, fill=False, padding=0)

        self.btn_draw_mode = Gtk.Button()
        self.btn_draw_mode.set_image(Gtk.Image.new_from_file("icons/draw_mode.png"))
        self.btn_draw_mode.connect("clicked", self.btn_draw_mode_clicked)
        self.hbox_top.pack_start(self.btn_draw_mode, expand=False, fill=False, padding=0)

        self.btn_content_mode = Gtk.Button()
        self.btn_content_mode.set_image(Gtk.Image.new_from_file("icons/contenttool_mode.png"))
        self.btn_content_mode.connect("clicked", self.btn_content_mode_clicked)
        self.hbox_top.pack_start(self.btn_content_mode, expand=False, fill=False, padding=0)

        #Close button
        self.btn_close = Gtk.Button()
        self.btn_close.set_image(Gtk.Image.new_from_file("icons/close_small.png"))
        self.btn_close.connect("clicked", self.btn_close_clicked)
        self.headerBar.pack_end(self.btn_close)

        #Loop button
        self.btn_loop = Gtk.Button()
        self.btn_loop_WhiteIcon = Gtk.Image.new_from_file("icons/loopWhite.png")
        self.btn_loop_GreenIcon = Gtk.Image.new_from_file("icons/loopGreen.png")
        self.btn_loop.set_image(self.btn_loop_WhiteIcon)
        self.btn_loop.connect("clicked", self.btn_loop_clicked)
        self.headerBar.pack_end(self.btn_loop)

        #Play button
        self.btn_playpause = Gtk.Button()
        self.btn_playpause_WhiteIcon = Gtk.Image.new_from_file("icons/play_pauseWhite.png")
        self.btn_playpause_GreenIcon = Gtk.Image.new_from_file("icons/play_pauseGreen.png")
        self.btn_playpause.set_image(self.btn_playpause_WhiteIcon)
        self.btn_playpause.connect("clicked", self.btn_playStop_clicked) # 5fa358ff  play state color
        self.headerBar.pack_end(self.btn_playpause)

        #Metronome button
        self.btn_metronome = Gtk.Button()
        self.btn_metronome.set_image(Gtk.Image.new_from_file("icons/metronome.png"))
        self.btn_metronome.connect("clicked", self.btn_metronome_clicked)
        self.headerBar.pack_end(self.btn_metronome)

        #SOLO cancel button
        self.btn_solo_cancel = Gtk.Button.new_with_label("")
        self.btn_solo_cancel.get_child().set_markup("<span weight='bold' size='large' color='#52824e'>Cancel\nSOLO</span>")
        self.btn_solo_cancel.get_child().set_justify(Gtk.Justification.CENTER)
        self.btn_solo_cancel.connect("clicked", self.btn_solo_cancel_clicked)
        self.headerBar.pack_end(self.btn_solo_cancel)

        # Jog-Wheel mode selector
        self.wheel_frame = Gtk.Frame(label="  Wheel Mode  ")
        #self.wheel_frame.set_shadow_type(Gtk.ShadowType.NONE)
        self.wheel_frame.set_shadow_type(Gtk.ShadowType.IN)
        self.wheel_hbox = Gtk.HBox()
        self.wheel_hbox.set_border_width(2)
        self.wheel_frame.add(self.wheel_hbox)

        self.btn_jog_mode = simplebuttonwidget.SimpleButton("JOG", "#FFFF00")
        self.btn_jog_mode.set_size_request(80, -1)
        self.wheel_hbox.pack_start(self.btn_jog_mode, expand=False, fill=False, padding=2)
        self.btn_jog_mode.connect("clicked", self.on_jog_mode_changed)

        self.btn_scrub_mode = simplebuttonwidget.SimpleButton("SCRUB", "#FFFF00")
        self.btn_scrub_mode.set_size_request(80, -1)
        self.wheel_hbox.pack_start(self.btn_scrub_mode, expand=False, fill=False, padding=2)
        self.btn_scrub_mode.connect("clicked", self.on_jog_mode_changed)

        self.btn_scroll_mode = simplebuttonwidget.SimpleButton("Scroll", "#FFFF00")
        self.btn_scroll_mode.set_size_request(80, -1)
        self.wheel_hbox.pack_start(self.btn_scroll_mode, expand=False, fill=False, padding=2)
        self.btn_scroll_mode.connect("clicked", self.on_jog_mode_changed)

        self.btn_rgain_mode = simplebuttonwidget.SimpleButton("R.Gain", "#FFFF00")
        self.btn_rgain_mode.set_size_request(80, -1)
        self.wheel_hbox.pack_start(self.btn_rgain_mode, expand=False, fill=False, padding=2)
        self.btn_rgain_mode.connect("clicked", self.on_jog_mode_changed)

        self.btn_marker_mode = simplebuttonwidget.SimpleButton("Marker", "#FFFF00")
        self.btn_marker_mode.set_size_request(80, -1)
        self.wheel_hbox.pack_start(self.btn_marker_mode, expand=False, fill=False, padding=2)
        self.btn_marker_mode.connect("clicked", self.on_jog_mode_changed)

        self.jog_mode = "" #Init with no mode selected
        self.headerBar.pack_end(self.wheel_frame)

        # Jog-Wheel off timer
        self.JogWheel_timer_id = None

        # Session save button
        self.btn_session_save = Gtk.Button()
        self.btn_session_save.set_image(Gtk.Image.new_from_file("icons/save_icon.png"))
        self.btn_session_save.connect("clicked", self.btn_session_save_clicked)
        self.hbox_top.pack_start(self.btn_session_save, expand=False, fill=False, padding=0)

        # Refresh button All
        self.btn_refresh_ALL = Gtk.Button()
        self.btn_refresh_ALL.set_image(Gtk.Image.new_from_file("icons/reload_32.png"))
        self.btn_refresh_ALL.connect("clicked", self.refresh_strip_list_ALL)
        self.hbox_top.pack_start(self.btn_refresh_ALL, expand=False, fill=False, padding=0)

        #Connection heartbeat LED
        self.LED_OSCconnection = LEDWidget.LEDWidget("OSC Offline", "#00FF00")
        self.LED_OSCconnection.set_size_request(100, 10)
        self.hbox_top.pack_end(self.LED_OSCconnection, expand=False, fill=False, padding=0)

        self.LED_OSCconnection.set_value(False)

        # Mode buttons VCA and TRack/Bus
        self.btn_activate_VCA_mode =  simplebuttonwidget.SimpleButton("VCA's", "#ff6641")
        self.btn_activate_VCA_mode.set_size_request(100, 100);
        self.btn_activate_VCA_mode.set_active_state(False)
        self.btn_activate_VCA_mode.connect("clicked", self.btn_VCA_mode_clicked)
        self.headerBar.pack_end(self.btn_activate_VCA_mode)
        self.btn_activate_TrkBus_mode =  simplebuttonwidget.SimpleButton("STRIPS", "#42d387")
        self.btn_activate_TrkBus_mode.set_size_request(100, 100);
        self.btn_activate_TrkBus_mode.set_active_state(True)
        self.btn_activate_TrkBus_mode.connect("clicked", self.btn_TrkBus_mode_clicked)
        self.headerBar.pack_end(self.btn_activate_TrkBus_mode)

        # Global bool to store loop state
        self.bLooping = False

        # Stack to hold strip view and edit modes
        self.stack = Gtk.Stack()
        self.stack.set_transition_duration(250)

        #Add the strip select table
        self.strip_table = stripTable.StripTable(8, 120, self.PIXELS_X_SECOND) #Limit to 120 tracks
        self.strip_table.connect("bank_channel_fader_changed", self.bank_channel_fader_changed)
        self.strip_table.connect("bank_channel_fader_gain_changed", self.bank_channel_fader_gain_changed)
        self.strip_table.connect("bank_channel_solo_changed", self.bank_channel_solo_changed)
        self.strip_table.connect("bank_channel_mute_changed", self.bank_channel_mute_changed)
        self.strip_table.connect("bank_channel_rec_changed", self.bank_channel_rec_changed)
        self.strip_table.connect("bank_channel_select_changed", self.bank_channel_select_changed)
        self.strip_table.connect("bank_channel_ssid_name_changed", self.bank_channel_ssid_name_changed)
        self.strip_table.connect("bank_channel_type_changed", self.bank_channel_type_changed)
        self.strip_table.connect("strip_select_changed", self.strip_select_changed)
        self.vbox_top.pack_start(self.strip_table, expand=True, fill=True, padding=0)

        #Add a separator
        self.bank_separator = Gtk.Image.new_from_file("icons/bank_spacer.png")
        self.vbox_top.pack_start(self.bank_separator, expand=False, fill=False, padding=0)

        # Build the bottom part of the gui, bank settings
        self.table_bank = Gtk.Grid()
        self.table_bank.set_column_homogeneous(True)
        self.strips_list_selbank = []

        self.stack.add_named(self.vbox_top, "strip_list")

        self.add(self.stack)

        for i in range(0, 8):
            self.strips_list_selbank.append(stripctlwidget.StripCtlWidget())
            self.table_bank.attach(self.strips_list_selbank[i], i, 0, 1, 1)
            self.strips_list_selbank[i].connect("strip_edit", self.bank_edit_clicked)
            self.strips_list_selbank[i].connect("strip_selected", self.bank_sel_clicked)
            self.strips_list_selbank[i].connect("solo_changed", self.bank_solo_clicked)
            self.strips_list_selbank[i].connect("mute_changed", self.bank_mute_clicked)
            self.strips_list_selbank[i].connect("rec_changed", self.bank_rec_clicked)
            self.strips_list_selbank[i].connect("spill_changed", self.bank_spill_clicked)
        self.vbox_top.pack_end(self.table_bank, expand=False, fill=False, padding=0)

        # Adding the AVR serial control object
        self.faderCtl = bankAvrController.BankAvrController(serial_port, baudrate, FADER_MIN, FADER_MAX)
        self.faderCtl.connect("encoder_increment", self.on_encoder_incremented)
        self.faderCtl.connect("fader_bank_mode_changed", self.fader_bank_mode_changed)
        self.faderCtl.connect("fader_bank_mode_untouched", self.fader_bank_mode_untouched)
        self.faderCtl.connect("trim_single_mode_changed", self.trim_single_mode_changed)
        self.faderCtl.connect("trim_single_mode_untouched", self.trim_single_mode_untouched)
        self.faderCtl.connect("fader_single_mode_changed", self.fader_single_mode_changed)
        self.faderCtl.connect("fader_single_mode_untouched", self.fader_single_mode_untouched)
        self.faderCtl.connect("pan_pos_single_mode_changed", self.pan_pos_single_mode_changed)
        self.faderCtl.connect("pan_pos_single_mode_untouched", self.pan_pos_single_mode_untouched)
        self.faderCtl.connect("pan_width_single_mode_changed", self.pan_width_single_mode_changed)
        self.faderCtl.connect("pan_width_single_mode_untouched", self.pan_width_single_mode_untouched)
        self.faderCtl.connect("send_single_mode_changed", self.send_single_mode_changed)
        self.faderCtl.connect("send_single_mode_untouched", self.send_single_mode_untouched)

        # Measure time between encoder ticks and speed
        self.encoder_last_time =  time.monotonic()
        self.encoder_speed = 0.0
        self.encoder_ticks_marker_counter = 0

        # Vars for encoder throttling
        self.last_encoder_speed_time = 0.0

        #Load encoder config from XML
        xml_encoder = root.find('encoder')
        self.encoder_reverse = ast.literal_eval(xml_encoder.find('reverse_dir').text)
        self.encoder_accel = ast.literal_eval(xml_encoder.find('acceleration').text)
        self.encoder_ticks_for_marker = ast.literal_eval(xml_encoder.find('ticks_for_marker').text)

        self.connect("destroy", self.destroy)
        self.connect("delete_event", self.delete_event)

        # Build the Edit mode window
        self.eVBox = Gtk.VBox()
        self.eHBox_title = Gtk.HBox()
        self.eHBox_title.set_border_width(10)
        self.eHBox_title.set_spacing(10)
        self.eVBox.pack_start(self.eHBox_title, expand=False, fill=True, padding=0)

        self.eBtn_close = Gtk.Button()
        self.eBtn_close.set_image(Gtk.Image.new_from_file("icons/close.png"))
        self.eHBox_title.pack_end(self.eBtn_close, expand=False, fill=True, padding=0)

        self.eBtn_next = Gtk.Button()
        self.eBtn_next.set_image(Gtk.Image.new_from_file("icons/next.png"))
        self.eHBox_title.pack_end(self.eBtn_next, expand=False, fill=True, padding=0)

        self.eBtn_prev = Gtk.Button()
        self.eBtn_prev.set_image(Gtk.Image.new_from_file("icons/prev.png"))
        self.eHBox_title.pack_start(self.eBtn_prev, expand=False, fill=True, padding=0)

        self.eLbl_title = Gtk.Label()
        self.eLbl_title.set_markup("<span weight='bold' size='xx-large' color='red'>No strip selected!</span>")
        self.eHBox_titleLbls = Gtk.HBox()
        self.eHBox_titleLbls.set_spacing(5)
        self.eHBox_title.pack_start(self.eHBox_titleLbls, expand=True, fill=False, padding=0)
        self.eHBox_titleLbls.pack_start(self.eLbl_title, expand=False, fill=False, padding=0)
        self.eLbl_ssid = Gtk.Label()
        self.eHBox_titleLbls.pack_start(self.eLbl_ssid, expand=False, fill=False, padding=0)

        self.eBtn_close.connect("clicked", self.eBtn_close_clicked)
        self.eBtn_next.connect("clicked", self.eBtn_next_clicked)
        self.eBtn_prev.connect("clicked", self.eBtn_prev_clicked)

        #Edit HBox
        self.eHBox_edit = Gtk.HBox()
        self.eVBox.pack_start(self.eHBox_edit, expand=True, fill=True, padding=0)

        #Left Buttons
        self.eHBox_chButtons = Gtk.HBox()
        self.eHBox_chButtons.set_spacing(5)
        self.eHBox_chButtons.set_border_width(7)
        self.eVBox_buttonsLeft = Gtk.VBox()
        self.eVBox_buttonsLeft.set_spacing(5)
        self.eVBox_buttonsLeft.set_border_width(7)
        self.eHBox_chButtons.pack_start(self.eVBox_buttonsLeft, expand=False, fill=False, padding=0)
        self.eHBox_edit.pack_start(self.eHBox_chButtons, expand=False, fill=False, padding=0)

        #Labels to indicate in/out channels
        self.eFrame_inouts = customframewidget.CustomFrame(stripselwidget.StripEnum.Empty)
        self.eVBox_insoutslbl = Gtk.VBox()
        self.eVBox_insoutslbl.set_spacing(10)
        self.eVBox_insoutslbl.set_border_width(10)
        self.eLbl_chnnalestitle = Gtk.Label()
        self.eLbl_chnnalestitle.set_text("Channels")
        self.eVBox_insoutslbl.pack_start(self.eLbl_chnnalestitle, expand=False, fill=False, padding=0)
        self.eLbl_ins = Gtk.Label()
        self.eLbl_ins.set_text("In: ##")
        self.eVBox_insoutslbl.pack_start(self.eLbl_ins, expand=False, fill=False, padding=0)
        self.eLbl_outs = Gtk.Label()
        self.eLbl_outs.set_text("Out: ##")
        self.eVBox_insoutslbl.pack_start(self.eLbl_outs, expand=False, fill=False, padding=0)
        self.eFrame_inouts.add(self.eVBox_insoutslbl)
        self.eVBox_buttonsLeft.pack_start(self.eFrame_inouts, expand=False, fill=False, padding=0)

        self.eBtn_phase = simplebuttonwidget.SimpleButton("", "#81A7FF", simplebuttonwidget.ButtonType.PHASE_SYMBOL)
        self.eVBox_buttonsLeft.pack_start(self.eBtn_phase, expand=False, fill=False, padding=0)

        self.eBtn_rec = simplebuttonwidget.SimpleButton("REC", "#FF0000")
        self.eVBox_buttonsLeft.pack_start(self.eBtn_rec, expand=False, fill=False, padding=0)
        self.eBtn_mute = simplebuttonwidget.SimpleButton("MUTE", "#FFFF00")
        self.eVBox_buttonsLeft.pack_start(self.eBtn_mute, expand=False, fill=False, padding=0)

        self.eVBox_buttonsLeft2 = Gtk.VBox()
        self.eVBox_buttonsLeft2.set_spacing(5)
        self.eVBox_buttonsLeft2.set_border_width(7)
        self.eHBox_chButtons.pack_start(self.eVBox_buttonsLeft2, expand=False, fill=False, padding=0)

        self.eFrame_solo = customframewidget.CustomFrame(stripselwidget.StripEnum.Empty)
        self.eVBox_solo = Gtk.VBox()
        self.eVBox_solo.set_border_width(7)
        self.eFrame_solo.add(self.eVBox_solo)
        self.eLbl_solo = Gtk.Label()
        self.eLbl_solo.set_text("Solo mode")
        self.eVBox_solo.pack_start(self.eLbl_solo, expand=False, fill=False, padding=0)
        self.eBtn_solo = simplebuttonwidget.SimpleButton("SOLO", "#00FF00")
        self.eBtn_soloIso = simplebuttonwidget.SimpleButton("Iso", "#81A7FF")
        self.eBtn_soloIso.set_size_request(-1,40)
        self.eBtn_soloLock = simplebuttonwidget.SimpleButton("Lock", "#81A7FF")
        self.eBtn_soloLock.set_size_request(-1, 40)
        self.eVBox_solo.pack_start(self.eBtn_solo, expand=False, fill=False, padding=0)
        self.eVBox_solo.pack_start(self.eBtn_soloIso, expand=False, fill=False, padding=0)
        self.eVBox_solo.pack_start(self.eBtn_soloLock, expand=False, fill=False, padding=0)
        self.eVBox_buttonsLeft2.pack_start(self.eFrame_solo, expand=False, fill=False, padding=0)

        # Monitor state
        self.eFrame_monitor = customframewidget.CustomFrame(stripselwidget.StripEnum.Empty)
        self.eVBox_monitor = Gtk.VBox()
        self.eVBox_monitor.set_border_width(7)
        self.eFrame_monitor.add(self.eVBox_monitor)
        self.eLbl_monitor = Gtk.Label()
        self.eLbl_monitor.set_text("Monitor")
        self.eVBox_monitor.pack_start(self.eLbl_monitor, expand=False, fill=False, padding=0)
        self.eBtn_monitorIn = simplebuttonwidget.SimpleButton("Input", "#81A7FF")
        self.eBtn_monitorIn.set_size_request(-1, 40)
        self.eVBox_monitor.pack_start(self.eBtn_monitorIn, expand=False, fill=False, padding=0)
        self.eBtn_monitorDisk = simplebuttonwidget.SimpleButton("Disk", "#81A7FF")
        self.eBtn_monitorDisk.set_size_request(-1, 40)
        self.eVBox_monitor.pack_start(self.eBtn_monitorDisk, expand=False, fill=False, padding=0)
        self.eVBox_buttonsLeft2.pack_start(self.eFrame_monitor, expand=False, fill=False, padding=0)

        #Left buttons signals connect
        self.eBtn_phase.connect("clicked", self.edit_phaseBtn_clicked)
        self.eBtn_rec.connect("clicked", self.edit_recBtn_clicked)
        self.eBtn_mute.connect("clicked", self.edit_muteBtn_clicked)
        self.eBtn_solo.connect("clicked", self.edit_soloBtn_clicked)
        self.eBtn_soloIso.connect("clicked", self.edit_soloIsoBtn_clicked)
        self.eBtn_soloLock.connect("clicked", self.eBtn_soloLock_clicked)
        self.eBtn_monitorIn.connect("clicked", self.eBtn_monIn_clicked)
        self.eBtn_monitorDisk.connect("clicked", self.eBtn_monDisk_clicked)

        # Add the sends select table
        self.eFrame_sends = customframewidget.CustomFrame(stripselwidget.StripEnum.Empty)
        self.eVBox_sends = Gtk.VBox()
        self.eVBox_sends.set_border_width(2)
        self.eFrame_sends.add(self.eVBox_sends)
        self.eLbl_Sends = Gtk.Label()
        self.eLbl_Sends.set_markup("<span weight='bold' size='xx-large' color='white'>Sends</span>")
        self.eVBox_sends.pack_start(self.eLbl_Sends, expand=False, fill=False, padding=0)

        max_sends_controls = 20
        self.sends_table = stripTable.StripTable(4, max_sends_controls, None, True) #Limit to 20 channels of sends
        for i in range(0, max_sends_controls):
            self.sends_table.register_strip(i+1, "###", stripTypes.StripEnum.AudioBus,
                                          False, False, False, 1, 1)

        self.sends_table.connect("bank_channel_mute_changed", self.bank_send_active_changed)
        self.sends_table.connect("bank_channel_fader_changed", self.bank_send_fader_changed)
        self.sends_table.connect("bank_channel_fader_gain_changed", self.bank_send_fader_gain_changed)
        self.sends_table.connect("bank_channel_ssid_name_changed", self.bank_send_ssid_name_changed)
        self.sends_table.connect("strip_select_changed", self.send_select_changed)

        self.sends_table.set_size_request(638, -1)
        self.eVBox_sends.pack_start(self.sends_table, expand=True, fill=True, padding=0)
        self.eHBox_edit.pack_end(self.eFrame_sends, expand=False, fill=True, padding=0)

        #Add spacer
        self.bank_separator_edit = Gtk.Image.new_from_file("icons/bank_spacer.png")
        self.eVBox.pack_start(self.bank_separator_edit, expand=False, fill=False, padding=0)

        # The faders widgets
        self.table_bank_edit = Gtk.Grid()
        self.table_bank_edit.set_column_homogeneous(True)
        self.eVBox.pack_end(self.table_bank_edit, expand=False, fill=False, padding=0)
        self.stack.add_named(self.eVBox, "edit_mode")

        #Trim gain
        self.eTrimCtl = selectFaderCtlWidget.SelectFaderCtlWidget("Trim")
        self.table_bank_edit.attach(self.eTrimCtl, 0, 0, 1, 1)
        self.eTrimCtl.connect("automation_changed", self.edit_trimdB_automation_changed)

        #Fader gain
        self.eFaderCtl = selectFaderCtlWidget.SelectFaderCtlWidget("Fader")
        self.table_bank_edit.attach(self.eFaderCtl, 1, 0, 1, 1)
        self.eFaderCtl.connect("automation_changed", self.edit_fader_automation_changed)

        #Panner
        self.ePanner = selectFaderCtlWidget.SelectFaderCtlWidget("Stereo Panner", True)
        self.table_bank_edit.attach(self.ePanner, 2, 0, 2, 1)
        self.ePanner.connect("automation_changed", self.edit_panner_automation_changed)

        #Sends
        self.eSendsCtl = []
        for i in range(0, 4):
            self.eSendsCtl.append(selectFaderCtlWidget.SelectFaderCtlWidget(str(i), isSend = True))
            self.eSendsCtl[i].connect("send_active_changed", self.edit_send_active_changed)
            #TODO there si no OSC message in Ardour 8.12 to change automation mode of a send yet, when available connect the signals
            self.table_bank_edit.attach(self.eSendsCtl[i], 4 + i, 0, 1, 1)

        # Connect OSC message received signals
        self.oscserver.connect("list_reply_track", self.list_osc_reply_track)
        self.oscserver.connect("list_reply_bus", self.list_osc_reply_bus)
        self.oscserver.connect("list_reply_end", self.list_osc_reply_end)
        #self.oscserver.connect("strip_list_changed", self.list_osc_changed) #TODO disconnected I'm not sure if i want it...
        self.oscserver.connect("fader_changed", self.fader_osc_changed)
        self.oscserver.connect("fader_gain_changed", self.fader_gain_osc_changed)
        self.oscserver.connect("solo_changed", self.solo_osc_changed)
        self.oscserver.connect("mute_changed", self.mute_osc_changed)
        self.oscserver.connect("rec_changed", self.rec_osc_changed)
        self.oscserver.connect("select_changed", self.select_osc_changed)
        self.oscserver.connect("meter_changed", self.meter_osc_changed)
        self.oscserver.connect("smpte_changed", self.smpte_osc_changed)
        if log_invalid_messages:
            self.oscserver.connect("unknown_message", self.unknown_osc_message)
        self.smpte_timer_ID = GLib.timeout_add(100, self.smpte_timeout)  # Create a timer

        # Connect OSC messages for the edit mode
        self.oscserver.connect("select_name_changed", self.select_name_osc_changed)
        self.oscserver.connect("select_phase_changed", self.select_phase_osc_changed)
        self.oscserver.connect("select_rec_changed", self.select_rec_osc_changed)
        self.oscserver.connect("select_mute_changed", self.select_mute_osc_changed)
        self.oscserver.connect("select_solo_changed", self.select_solo_osc_changed)
        self.oscserver.connect("select_soloIso_changed", self.select_soloIso_osc_changed)
        self.oscserver.connect("select_soloLock_changed", self.select_soloLock_osc_changed)
        self.oscserver.connect("select_monitorIn_changed", self.select_monitorIn_osc_changed)
        self.oscserver.connect("select_monitorDisk_changed", self.select_monitorDisk_osc_changed)
        self.oscserver.connect("select_ninputs_changed", self.select_nInputs_osc_changed)
        self.oscserver.connect("select_noutputs_changed", self.select_nOutputs_osc_changed)
        self.oscserver.connect("select_trimdB_changed", self.select_trimdB_osc_changed)
        self.oscserver.connect("select_fader_changed", self.select_fader_osc_changed)
        self.oscserver.connect("select_fader_gain_changed", self.select_fader_gain_osc_changed)
        self.oscserver.connect("select_pan_pos_changed", self.select_panPos_osc_changed)
        self.oscserver.connect("select_pan_width_changed", self.select_panWidth_osc_changed)
        self.oscserver.connect("select_panner_must_have_width_control_changed", self.select_panner_width_control_osc_changed)
        self.oscserver.connect("select_trimdB_automation_changed", self.select_trimdB_automation_osc_changed)
        self.oscserver.connect("select_fader_automation_changed", self.select_fader_automation_osc_changed)
        self.oscserver.connect("select_pan_position_automation_changed", self.select_pan_position_automation_osc_changed)
        self.oscserver.connect("select_pan_width_automation_changed", self.select_pan_width_automation_osc_changed)
        self.oscserver.connect("select_send_name_changed", self.select_send_name_osc_changed)
        self.oscserver.connect("select_send_enable_changed", self.select_send_enable_osc_changed)
        self.oscserver.connect("select_send_fader_changed", self.select_send_fader_osc_changed)
        self.oscserver.connect("select_send_gain_changed", self.select_send_gain_osc_changed)
        self.oscserver.connect("strip_name_changed", self.strip_name_osc_changed)
        self.oscserver.connect("osc_heartbeat_tick", self.osc_heartbeat_tick)

        self.set_size_request(window_width, window_height)
        self.show_all()
        self.show()

        #Hide widgets in the fader control bank (bottom)
        for selbank in self.strips_list_selbank:
            selbank.set_strip_type(StripEnum.Empty)

        #Start with all send strips hidden, must be done here after the show_all() of the main screen
        for i in range(0, self.sends_table.get_number_of_strips()):
            self.sends_table.hide_strip(i+1)

        # Set theme
        screen = Gdk.Screen.get_default()
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("saptouch_theme.css")

        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        #Watchdog timer to manage OSC connection
        self.watchdog = oscconnectionwatchdog.OSCConnectionWatchdog(callback=self.on_watchdog_expired)
        self.watchdog.start()

        # Maximize
        if window_maximize:
            self.maximize()

    def main(self):
        self.oscserver.start()
        Gtk.main()


print(__name__)
if __name__ == "__main__":
    base = ControllerGUI()
    base.main()
