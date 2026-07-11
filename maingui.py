#!/usr/bin/env python

import gi

from stripTypes import StripEnum

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

import liblo
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

        resp = quitDialog.run()
        quitDialog.destroy()
        if resp == Gtk.ResponseType.YES:
            self.oscserver.stop()
            self.faderCtl.close()
            return False

        # Keep the application open
        return True

    def destroy(self, widget):
        Gtk.main_quit()

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

    def on_encoder_incremented(self, event, value):
        jog_mode = self.CB_JogWheel_mode.get_active_text()
        if jog_mode == "Jog":
            liblo.send(self.target, "/jog/mode", 0)
            liblo.send(self.target, "/jog", value*0.2)
        elif jog_mode == "Scrub":
            liblo.send(self.target, "/jog/mode", 2)
            liblo.send(self.target, "/jog", value*0.1)
        elif jog_mode == "Scroll":
            liblo.send(self.target, "/jog/mode", 5)
            if value > 0:
                liblo.send(self.target, "/jog", 1)
            else:
                liblo.send(self.target, "/jog", -1)
        elif jog_mode == "R.Gain":
            if value > 0:
                liblo.send(self.target, "/access_action/Region/boost-region-gain")
            else:
                liblo.send(self.target, "/access_action/Region/cut-region-gain")

    def fader_bank_mode_changed(self, event, channel, value):
        if self.strip_table_tracks.get_number_of_strips() > 0:  # Only if we have strip list from DAW
            selSSID = self.strips_list_selbank[channel].get_ssid()
            if selSSID is not None:
                liblo.send(self.target, "/strip/fader/touch", selSSID, 1)  # Using floats it works
                liblo.send(self.target, "/strip/fader", selSSID, value)
        return True

    def fader_bank_mode_untouched(self, event, value):
        if self.strip_table_tracks.get_number_of_strips() > 0:  # Only if we have strip list from DAW
            # print("Unotuch event: %x", value)
            for i in range(0, 8):
                if value & (1 << i):
                    selSSID = self.strips_list_selbank[i].get_ssid()
                    if selSSID is not None:
                        liblo.send(self.target, "/strip/fader/touch", selSSID, 0)
        return True

    def trim_single_mode_changed(self, event, value):
        liblo.send(self.target, "/select/trimdB/touch", 1)
        liblo.send(self.target, "/select/trimdB", value)
        return True

    def trim_single_mode_untouched(self, event):
        liblo.send(self.target, "/select/trimdB/touch", 0)
        return True

    def fader_single_mode_changed(self, event, value):
        liblo.send(self.target, "/select/fader/touch", 1)
        liblo.send(self.target, "/select/fader", value)
        return True

    def fader_single_mode_untouched(self, event):
        liblo.send(self.target, "/select/fader/touch", 0)
        return True

    def pan_pos_single_mode_changed(self, event, value):
        # TODO enable touch automation when available in Ardour

        #TODO tha PAN control seams to be wrong, autmation failing, wide control on mono channels! revise!

        # liblo.send(self.target, "/select/pan_stereo_position/touch", 1)

        # Prefer center point (0.5)
        corrected_pan_val = value
        dist_2_center = abs(corrected_pan_val - 0.5)
        if dist_2_center < 0.05:
            corrected_pan_val = 0.5

        liblo.send(self.target, "/select/pan_stereo_position", corrected_pan_val)
        return True

    def pan_pos_single_mode_untouched(self, event):
        # TODO enable touch automation when available in Ardour
        # liblo.send(self.target, "/select/pan_stereo_position/touch", 0)
        return True

    def pan_width_single_mode_changed(self, event, value):
        # TODO enable touch automation when available in Ardour
        # liblo.send(self.target, "/select/pan_stereo_width/touch", 1)

        #Prefer center point (0.5)
        corrected_pan_val = value
        dist_2_center = abs(corrected_pan_val - 0.5)
        if dist_2_center < 0.05:
            corrected_pan_val = 0.5

        #TODO I believe this is an ardour bug but pan must be sent between -1 and 1
        corrected_pan_val = corrected_pan_val * 2.0 - 1.0

        #TODO do not send width for mono strips!!!! Also force with to stay fix for mono strips in their pan widget
        liblo.send(self.target, "/select/pan_stereo_width", corrected_pan_val)
        return True

    def pan_width_single_mode_untouched(self, event):
        # TODO enable touch automation when available in Ardour
        # liblo.send(self.target, "/select/pan_stereo_width/touch", 0)
        return True

    def send_single_mode_changed(self, event, channel, value):
        if self.sends_table.get_number_of_strips() > 0:  # Only if we have strip list from DAW
            selSSID = self.eSendsCtl[channel].get_sendID()
            if selSSID is not None:
                # TODO enable touch automation when available in Ardour (Unhandled OSC message: /select/send/touch i:3 i:1)
                #liblo.send(self.target, "/select/send/touch", selSSID, 1)
                liblo.send(self.target, "/select/send_fader", selSSID, value)
            else:
                #Restore fader to zero
                self.faderCtl.move_single_send(channel, 0.0)
        return True

    def send_single_mode_untouched(self, event, channel):
        selSSID = self.eSendsCtl[channel].get_sendID()
        # TODO enable touch automation when available in Ardour (Unhandled OSC message: /select/send/touch i:3 i:1)
        #if selSSID is not None:
            #liblo.send(self.target, "/select/send/touch", selSSID, 0)
        return True

    def strip_select_changed(self, widget, issid):
        self.safe_strip_select(issid)

    def refresh_strip_list_ALL(self, widget):
        self.strip_table_tracks.clear_strips()
        self.strip_table_VCA.clear_strips()

        # Config the surface as infinite banks, track setting, strip feedback and fader as position values
        liblo.send(self.target, "/set_surface", 0, 23, 24771, 2, 0)  # Check Ardour OSC preferences for reference of these values
        # the feedback value of 24771 includes the level meters as text and the changes the #reply messages to /reply

        liblo.send(self.target, "/strip/list")

    def btn_VCA_mode_clicked(self, widget):
        if self.bVCAmode is not True:
            self.bSpill = False
            self.bVCAmode = True
            self.btn_activate_VCA_mode.set_active_state(True)
            self.btn_activate_TrkBus_mode.set_active_state(False)
            self.set_VCA_strip_view_mode()
            self.refresh_strip_list_ALL(None)

    def btn_TrkBus_mode_clicked(self, widget):
        if self.bVCAmode is True or self.bSpill is True:
            self.bSpill = False
            self.bVCAmode = False
            self.btn_activate_VCA_mode.set_active_state(False)
            self.btn_activate_TrkBus_mode.set_active_state(True)
            self.set_VCA_strip_view_mode()
            self.refresh_strip_list_ALL(None)

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
        self.bSpill = True
        self.bVCAmode = False
        self.btn_activate_VCA_mode.set_active_state(False)
        self.btn_activate_TrkBus_mode.set_active_state(True)
        self.set_VCA_strip_view_mode()
        liblo.send(self.target, "/strip/spill", ichannel)
        self.strip_table_tracks.clear_strips()
        self.strip_table_VCA.clear_strips()
        liblo.send(self.target, "/strip/list")

    def bank_mute_clicked(self, widget, ichannel, bvalue):
        liblo.send(self.target, "/strip/mute", ichannel, int(bvalue))

    def bank_solo_clicked(self, widget, ichannel, bvalue):
        liblo.send(self.target, "/strip/solo", ichannel, int(bvalue))

    # Callbacks from OSC incoming messages
    def fader_osc_changed(self, widget, ichannel, fvalue):
        #print("fader received on channel '%d' with value '%f'" % (ichannel, fvalue))
        self.strip_table_tracks.set_fader(ichannel, fvalue)
        self.strip_table_VCA.set_fader(ichannel, fvalue)

    def fader_gain_osc_changed(self, widget, ichannel, fvalue):
        #print("fader received on channel '%d' with value '%f'" % (ichannel, fvalue))
        self.strip_table_tracks.set_fader_gain(ichannel, fvalue)
        self.strip_table_VCA.set_fader_gain(ichannel, fvalue)

    def solo_osc_changed(self, widget, ichannel, bvalue):
        # print "solo received on channel '%d' with state '%s'" % (ichannel, bvalue)
        self.strip_table_tracks.set_solo(ichannel, bvalue)
        self.strip_table_VCA.set_solo(ichannel, bvalue)

    def mute_osc_changed(self, widget, ichannel, bvalue):
        # print "mute received on channel '%d' with state '%s'" % (ichannel, bvalue)
        self.strip_table_tracks.set_mute(ichannel, bvalue)
        self.strip_table_VCA.set_mute(ichannel, bvalue)

    def rec_osc_changed(self, widget, ichannel, bvalue):
        # print "rec received on channel '%d' with state '%s'" % (ichannel, bvalue)
        self.strip_table_tracks.set_rec(ichannel, bvalue)

    def select_osc_changed(self, widget, ichannel, bvalue):
        # print "select received on channel '%d' with state '%s'" % (ichannel, bvalue)
        if not self.bVCAmode:
            self.strip_table_tracks.strip_select(ichannel, bvalue) #This is ok for track/bus since ssid is checked inside
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
        self.strip_table_tracks.set_meter(ichannel, fvalue)

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
        if type is stripTypes.StripEnum.AudioTrack or type is stripTypes.StripEnum.MidiTrack:
            self.strip_table_tracks.append_strip(ssid, name, type, mute, solo, rec, inputs, outputs)

    def list_osc_reply_bus(self, widget, ssid, name, type, mute, solo, inputs, outputs):
        if type is stripTypes.StripEnum.AudioBus or type is stripTypes.StripEnum.MidiBus:
            self.strip_table_tracks.append_strip(ssid, name, type, mute, solo, None, inputs, outputs)

        if type is stripTypes.StripEnum.VCA:
            if self.bSpill:
                #In Spill mode, append the VCA stripe together with strips
                self.strip_table_tracks.append_strip(ssid, name, type, mute, solo, None, inputs, outputs)
            else:
                self.strip_table_VCA.append_strip(ssid, name, type, mute, solo, None, inputs, outputs)

    def list_osc_reply_end(self, widget):
        self.strip_table_tracks.fill_strips()
        self.strip_table_VCA.fill_strips()

        if self.bVCAmode:
            #VCA MODE
            self.strip_table_tracks.reset_current_selected_bank()
            if self.strip_table_VCA.get_number_of_strips() > 0:
                self.safe_strip_select(self.strip_table_VCA.get_strip_ssid(0))

        else:
            #TRACK/BUS MODE
            self.strip_table_VCA.reset_current_selected_bank()
            if self.strip_table_tracks.get_number_of_strips() > 0:
                if self.iLastSelectedTrackBus_ssid is None:
                    self.safe_strip_select(self.strip_table_tracks.get_strip_ssid(0))
                else:
                    self.safe_strip_select(self.iLastSelectedTrackBus_ssid)

        if self.bSpill:
            if self.strip_table_tracks.get_number_of_strips() > 1:
                self.safe_strip_select(self.strip_table_tracks.get_strip_ssid(0)) #In VCA spill mode select always the first stripe
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

    #Edit Mode button signals
    def eBtn_close_clicked(self, widget):
        self.faderCtl.set_state(bankAvrController.FaderBankState.EIGHT_CHANNELS_FADERS)
        self.stack.set_visible_child_full("strip_list", Gtk.StackTransitionType.SLIDE_DOWN)
        self.btn_activate_VCA_mode.show()
        self.btn_activate_TrkBus_mode.show()

    def eBtn_next_clicked(self, widget):
        if self.strip_table_tracks.get_current_selected_strip_index() != None:
            next_select = self.strip_table_tracks.get_current_selected_strip_index() + 1
            if next_select == self.strip_table_tracks.get_number_of_strips():
                next_select = 0

            self.safe_strip_select(self.strip_table_tracks.get_strip_ssid(next_select))

    def eBtn_prev_clicked(self, widget):
        if self.strip_table_tracks.get_current_selected_strip_index() != None:
            next_select = self.strip_table_tracks.get_current_selected_strip_index() - 1
            if next_select == -1:
                next_select = self.strip_table_tracks.get_number_of_strips() - 1

            self.safe_strip_select(self.strip_table_tracks.get_strip_ssid(next_select))

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

    def select_trimdB_automation_osc_changed(self, widget, value):
        self.eTrimCtl.set_automation_mode(value)

    def select_fader_automation_osc_changed(self, widget, value):
        self.eFaderCtl.set_automation_mode(value)

    def select_send_name_osc_changed(self, widget, send_id, send_name):
        self.sends_table.set_strip_name(send_id, send_name)
        self.sends_table.show_strip(send_id)

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
        if self.strip_table_tracks.check_if_ssid_exists(ssid):
            if self.strip_table_tracks.get_current_selected_strip_ssid() != ssid:
                self.ePanner.set_panner_width(1.0) #If selected channel changed start assuiming full stereo width since mono and balance mode do not feedback this command
                self.faderCtl.move_single_pan_width(1.0) #set fader width at center
            liblo.send(self.target, "/strip/select", ssid, 0) #TODO I must send a zero not a 1 to select! this must be a bug in Ardour (8.12)!

        elif self.strip_table_VCA.check_if_ssid_exists(ssid):
            #print("VCA selWdiget clicked with ssid '%d'" % (ssid))
            self.strip_table_VCA.strip_select(ssid, True)  # This is ok for track/bus since ssid is checked inside

    # Set the view mode to see track/bus or VCA's
    def set_VCA_strip_view_mode(self):
        if self.bVCAmode:
            #Enableing VCA MODE
            self.strip_table_tracks.hide()
            self.strip_table_VCA.show()
        else:
            #Enableing TRACK/BUS MODE
            self.strip_table_VCA.hide()
            self.strip_table_tracks.show()

    def spill_mode_blink_timer(self):
        if self.bSpill:
            self.btn_activate_TrkBus_mode.set_active_state(not self.btn_activate_TrkBus_mode.get_active_state())
            self.btn_activate_TrkBus_mode.set_label("SPILLED\nSTRIPS")
            self.btn_activate_VCA_mode.set_active_state(self.btn_activate_TrkBus_mode.get_active_state())
            self.btn_activate_VCA_mode.set_label("SPILLED\nVCA")
        else:
            self.set_VCA_strip_view_mode()
            self.btn_activate_TrkBus_mode.set_label("STRIPS")
            self.btn_activate_VCA_mode.set_label("VCA's")
        return self.bSpill

    def __init__(self):
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
        self.headerBar.set_custom_title(self.ImgLogo)

        #Edit Mode buttons
        self.btn_smart_mode = Gtk.Button.new_with_label("")
        self.btn_smart_mode.get_child().set_markup("<span weight='bold' size='large' color='white'>Smart</span>")
        self.btn_smart_mode.connect("clicked", self.btn_smart_mode_clicked)
        self.headerBar.pack_start(self.btn_smart_mode)

        self.btn_object_mode = Gtk.Button()
        self.btn_object_mode.set_image(Gtk.Image.new_from_file("icons/object_mode.png"))
        self.btn_object_mode.connect("clicked", self.btn_object_mode_clicked)
        self.headerBar.pack_start(self.btn_object_mode)

        self.btn_range_mode = Gtk.Button()
        self.btn_range_mode.set_image(Gtk.Image.new_from_file("icons/range_mode.png"))
        self.btn_range_mode.connect("clicked", self.btn_range_mode_clicked)
        self.headerBar.pack_start(self.btn_range_mode)

        self.btn_cut_mode = Gtk.Button()
        self.btn_cut_mode.set_image(Gtk.Image.new_from_file("icons/cut_mode.png"))
        self.btn_cut_mode.connect("clicked", self.btn_cut_mode_clicked)
        self.headerBar.pack_start(self.btn_cut_mode)

        self.btn_timefx_mode = Gtk.Button()
        self.btn_timefx_mode.set_image(Gtk.Image.new_from_file("icons/timefx_mode.png"))
        self.btn_timefx_mode.connect("clicked", self.btn_timefx_mode_clicked)
        self.headerBar.pack_start(self.btn_timefx_mode)

        self.btn_draw_mode = Gtk.Button()
        self.btn_draw_mode.set_image(Gtk.Image.new_from_file("icons/draw_mode.png"))
        self.btn_draw_mode.connect("clicked", self.btn_draw_mode_clicked)
        self.headerBar.pack_start(self.btn_draw_mode)

        self.btn_content_mode = Gtk.Button()
        self.btn_content_mode.set_image(Gtk.Image.new_from_file("icons/contenttool_mode.png"))
        self.btn_content_mode.connect("clicked", self.btn_content_mode_clicked)
        self.headerBar.pack_start(self.btn_content_mode)

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
        self.btn_solo_cancel.get_child().set_markup("<span weight='bold' size='medium' color='#52824e'>Cancel\nSOLO</span>")
        self.btn_solo_cancel.get_child().set_justify(Gtk.Justification.CENTER)
        self.btn_solo_cancel.connect("clicked", self.btn_solo_cancel_clicked)
        self.headerBar.pack_end(self.btn_solo_cancel)

        # Jog-Wheel mode selector
        self.CB_JogWheel_mode = Gtk.ComboBoxText()
        self.CB_JogWheel_mode.append_text("Jog")
        self.CB_JogWheel_mode.append_text("Scrub")
        self.CB_JogWheel_mode.append_text("Scroll")
        self.CB_JogWheel_mode.append_text("R.Gain")
        self.CB_JogWheel_mode.set_active(0)
        self.headerBar.pack_end(self.CB_JogWheel_mode)
        lbl_wheelMode = Gtk.Label()
        lbl_wheelMode.set_markup("<span size='medium' color='white'>Wheel\nmode:</span>")
        self.headerBar.pack_end(lbl_wheelMode)

        # Session save button
        self.btn_session_save = Gtk.Button()
        self.btn_session_save.set_image(Gtk.Image.new_from_file("icons/save_icon.png"))
        self.btn_session_save.connect("clicked", self.btn_session_save_clicked)
        self.headerBar.pack_end(self.btn_session_save)

        # Refresh button All
        self.btn_refresh_ALL = Gtk.Button()
        self.btn_refresh_ALL.set_image(Gtk.Image.new_from_file("icons/reload_32.png"))
        self.btn_refresh_ALL.connect("clicked", self.refresh_strip_list_ALL)
        self.headerBar.pack_end(self.btn_refresh_ALL)

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
        self.strip_table_tracks = stripTable.StripTable(8, self.PIXELS_X_SECOND)
        self.strip_table_tracks.connect("bank_channel_fader_changed", self.bank_channel_fader_changed)
        self.strip_table_tracks.connect("bank_channel_fader_gain_changed", self.bank_channel_fader_gain_changed)
        self.strip_table_tracks.connect("bank_channel_solo_changed", self.bank_channel_solo_changed)
        self.strip_table_tracks.connect("bank_channel_mute_changed", self.bank_channel_mute_changed)
        self.strip_table_tracks.connect("bank_channel_rec_changed", self.bank_channel_rec_changed)
        self.strip_table_tracks.connect("bank_channel_select_changed", self.bank_channel_select_changed)
        self.strip_table_tracks.connect("bank_channel_ssid_name_changed", self.bank_channel_ssid_name_changed)
        self.strip_table_tracks.connect("bank_channel_type_changed", self.bank_channel_type_changed)
        self.strip_table_tracks.connect("strip_select_changed", self.strip_select_changed)
        self.vbox_top.pack_start(self.strip_table_tracks, expand=True, fill=True, padding=0)

        self.strip_table_VCA = stripTable.StripTable(8, self.PIXELS_X_SECOND, is_vca = True)
        self.strip_table_VCA.connect("bank_channel_fader_changed", self.bank_channel_fader_changed)
        self.strip_table_VCA.connect("bank_channel_fader_gain_changed", self.bank_channel_fader_gain_changed)
        self.strip_table_VCA.connect("bank_channel_solo_changed", self.bank_channel_solo_changed)
        self.strip_table_VCA.connect("bank_channel_mute_changed", self.bank_channel_mute_changed)
        self.strip_table_VCA.connect("bank_channel_select_changed", self.bank_channel_select_changed)
        self.strip_table_VCA.connect("bank_channel_ssid_name_changed", self.bank_channel_ssid_name_changed)
        self.strip_table_VCA.connect("bank_channel_type_changed", self.bank_channel_type_changed)
        self.strip_table_VCA.connect("strip_select_changed", self.strip_select_changed)
        self.vbox_top.pack_start(self.strip_table_VCA, expand=True, fill=True, padding=0)

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
        self.sends_table = stripTable.StripTable(4, None, True)
        self.sends_table.clear_strips()
        for i in range(0, 32):
            self.sends_table.append_strip(i+1, "###", stripTypes.StripEnum.AudioBus,
                                          False, False, False, 1, 1)
        self.sends_table.fill_strips()
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
        self.oscserver.connect("select_trimdB_automation_changed", self.select_trimdB_automation_osc_changed)
        self.oscserver.connect("select_fader_automation_changed", self.select_fader_automation_osc_changed)
        self.oscserver.connect("select_send_name_changed", self.select_send_name_osc_changed)
        self.oscserver.connect("select_send_enable_changed", self.select_send_enable_osc_changed)
        self.oscserver.connect("select_send_fader_changed", self.select_send_fader_osc_changed)
        self.oscserver.connect("select_send_gain_changed", self.select_send_gain_osc_changed)

        self.set_size_request(window_width, window_height)
        self.show_all()
        self.show()

        #Hide widgets in the fader control bank (bottom)
        for selbank in self.strips_list_selbank:
            selbank.set_strip_type(StripEnum.Empty)

        #Set the view according the boolean VCA mode
        self.set_VCA_strip_view_mode()

        #Start with all send strips hidden, must be donw here after the show_all() of the main screen
        for i in range(0, self.sends_table.get_number_of_strips()):
            self.sends_table.hide_strip(i+1)

        # Set theme
        screen = Gdk.Screen.get_default()
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("saptouch_theme.css")

        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

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
