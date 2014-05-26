#!/usr/bin/env python
# coding: utf-8

# WiiMote wrapper in pure Python
#
# Copyright (c) 2014 Raphael Wimmer <raphael.wimmer@ur.de>
#
# using code from gtkwhiteboard, http://stepd.org/gtkwhiteboard/
# Copyright (c) 2008 Stephane Duchesneau,
# which was modified by Pere Negre and Pietro Pilolli to work with the new WiiMote Plus:
# https://raw.githubusercontent.com/pnegre/python-whiteboard/master/stuff/linuxWiimoteLib.py
#
# LICENSE:         MIT (X11) License:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import bluetooth
import threading

VERSION = (0,1,0)
DEBUG = False

def find():
    """
    Uses Bluetooth SDP to find available Wiimotes. 
    Returns a list of (bt_addr, device_name) tuples.
    Only supported Wiimote devices are returned.
    """
    devices = bluetooth.find_service()
    wiimotes = []
    for device in devices:
        if device["name"] in KNOWN_DEVICES:
            wiimotes.append((device["host"], device["name"]))
    return wiimotes

def connect(btaddr, model=None):
    """
    Establishes a connection to the Wiimote at *btaddr* and returns a Wiimote
    object. If no *model* is specified, the model is determined automatically.
    """
    if model == None:
        model = bluetooth.lookup_name(btaddr)
    if model in KNOWN_DEVICES:
        return WiiMote(btaddr, model)
    else:
        raise Exception("Wiimote model '%s' unknown!" % (model))

def _debug(msg):
    if DEBUG:
        print("DEBUG: " + str(msg))

class Accelerometer(object):
   
    SUPPORTED_REPORTS = [0x31]

    def __init__(self, wiimote):
        self._state = [0.0, 0.0, 0.0]
        self._com = wiimote._com

    def __len__(self):
        return len(self._state)

    def __repr__(self):
        return repr(self._state)

    def __getitem__(self, axis):
        if 0 <= axis <= 2:
            return self._state[axis]
        else:
            raise IndexError("list index out of range")
    
    def handle_report(self, report):
        if report[0] in [0x3e, 0x3f]: # interleaved modes
            raise NotImplementedError("Data reporting mode 0x3e/0x3f not supported")
        x_msb, y_msb, z_msb = report[3:6]
        x = (x_msb << 2) + ((report[1] & 0b01100000) >> 5)
        y = (y_msb << 2) + ((report[2] & 0b00100000) >> 4)
        z = (z_msb << 2) + ((report[2] & 0b01000000) >> 5)
        self._state = [x, y, z]
                    
    def _register_callback(self, btn, func):
        pass # todo

    

class Buttons(object):
    
    BUTTONS = {'A': 0x0008,
               'B': 0x0004,
               'Down' : 0x0400,
               'Home': 0x0080,
               'Left': 0x0100,
               'Minus': 0x0010,
               'One': 0x0002,
               'Plus': 0x1000,
               'Right': 0x0200,
               'Two': 0x0001,
               'Up': 0x0800,
    }

    def __init__(self, wiimote):
        self._wiimote = wiimote
        self._com = wiimote._com
        self._state = {}
        for button in Buttons.BUTTONS.keys():
            self._state[button] = False

    def __len__(self):
        return len(self._state)

    def __repr__(self):
        return repr(self._state)

    def __getitem__(self, btn):
        if self._state.has_key(btn):
            return self._state[btn]
        else:
            raise KeyError(str(btn))

    def handle_report(self, report):
        btn_bytes = (report[1] << 8) + report[2]
        new_state = {}
        for btn, mask in Buttons.BUTTONS.items():
            new_state[btn] = bool(mask & btn_bytes)
        diff = self._update_state(new_state)

    def _update_state(self, new_state):
        diff = []
        for btn, state in new_state.items():
            if self._state[btn] != state:
                diff.append((btn, state))
                self._state[btn] = state
        return diff
                    
    def _register_callback(self, btn, func):
        pass # todo

class LEDs(object):

    def __init__(self, wiimote):
        self._state = [False, False, False, False]
        self.wiimote = wiimote

    def __len__(self):
        return len(self._state)

    def __repr__(self):
        return repr(self._state)

    def __getitem__(self, led_no):
        if 0 <= led_no <= 3:
            return self._state[led_no]
        else:
            raise IndexError("list index out of range")

    def __setitem__(self, led_no, val):
        new_led_state = self._state
        if 0 <= led_no <= 3:
            new_led_state[led_no] = True if val else False
            self.set_leds(new_led_state)
        else:
            raise IndexError("list index out of range")

    def set_leds(self, led_list):
        for led_no, val in enumerate(led_list):
            self._state[led_no] = True if val else False
        RPT_LED = 0x11
        led_byte = 0x00
        for val, state in zip([0x10, 0x20, 0x40, 0x80], self._state):
            if state:
               led_byte += val
        self.wiimote._com._send(RPT_LED, led_byte)
    

class Rumbler(object):

    def __init__(self, wiimote):
        self._state = False
        self.wiimote = wiimote

    def set_rumble(self, state):
        self._state = state
        self.wiimote._com.set_rumble(state)

    def rumble(self, length=0.5):
        t = threading.Timer(length, self.set_rumble, [False])
        t.start()
        self.set_rumble(True)


class CommunicationHandler(threading.Thread):
    
    MODE_DEFAULT = 0x30
    MODE_ACC     = 0x31

    RPT_STATUS_REQ = 0x15

    def __init__(self, wiimote):
        threading.Thread.__init__(self)
        self.rumble = False # rumble always 
        self.wiimote = wiimote
        self.btaddr = wiimote.btaddr
        self.model = wiimote.model
        self.reporting_mode = self.MODE_DEFAULT
        self._controlsocket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
        self._controlsocket.connect((self.btaddr, 17))
        self._datasocket = bluetooth.BluetoothSocket(bluetooth.L2CAP)
        self._datasocket.connect((self.btaddr, 19))
        if self.model == 'Nintendo RVL-CNT-01':
            self._sendsocket = self._controlsocket
            self._CMD_SET_REPORT = 0x52
        elif self.model == 'Nintendo RVL-CNT-01-TR':
            self._sendsocket = self._datasocket
            self._CMD_SET_REPORT = 0xa2
        else:
            raise Exception("unknown model")
        try:
            self._datasocket.settimeout(1)
        except NotImplementedError:
            print "socket timeout not implemented with this bluetooth module"
        self.set_report_mode(self.MODE_ACC)
    
    def _send(self, *bytes_to_send):
        _debug("sending " + str(bytes_to_send))
        data_str = chr(self._CMD_SET_REPORT)
        bytes_to_send = list(bytes_to_send)
        bytes_to_send[1] |= int(self.rumble)
        for b in bytes_to_send:
            data_str += chr(b)
        self._sendsocket.send(data_str)

    def run(self):
        self.running = True
        while self.running:
            try:
                data = map(ord,self._datasocket.recv(32))
            except bluetooth.BluetoothError:
                continue
            if len(data) < 2: # disconnect!
                self.running = False
            else:
                self._handle(data)
        self._dispose()

    def _dispose(self):
        self._datasocket.close()
        self._controlsocket.close()
        self.running = False

    def set_report_mode(self, mode):
        self.reporting_mode = mode
        self._send(0x12, 0x00, mode)

    def _handle(self, bytes_read):
        _debug(bytes_read)
        rpt_type = bytes_read[1]
        # all reports include button data
        self.wiimote.buttons.handle_report(bytes_read[1:])
        if rpt_type in Accelerometer.SUPPORTED_REPORTS:
            self.wiimote.accelerometer.handle_report(bytes_read[1:])

    def set_rumble(self, state):
        self.rumble = state
        # send any report to toggle rumble bit
        self._send(self.RPT_STATUS_REQ, int(state))

class WiiMote(object):

    # instance methods
    def __init__(self, btaddr, model):
        self.btaddr = btaddr
        self.model = model
        self.connected = False
        self._com = CommunicationHandler(self)
        self._leds = LEDs(self)
        self.accelerometer = Accelerometer(self)
        self.buttons = Buttons(self)
        self.rumbler = Rumbler(self)
        self._com.start()
 
    def _disconnect(self):
        pass

    def _get_capabilities(self):
        return None

    def _get_state(self):
        return None

    def _set_state(self, state):
        pass

    def _reset(self):
        pass

    ### LEDs ###

    def rumble(self, length=0.5):
        self.rumbler.rumble(length)
    
    def set_rumble(self, state):
        self.rumbler.set_rumble(state)

    def get_leds(self):
        return self._leds

    def set_leds(self, led_list):
        if len(led_list) != len(self._leds):
            raise IndexError("list length needs to be exactly %d!" % len(self._leds))
        else:
            self._leds.set_leds(led_list)

    leds = property(get_leds, set_leds)


    #rumble = property(get_rumble, set_rumble)

KNOWN_DEVICES = ['Nintendo RVL-CNT-01', 'Nintendo RVL-CNT-01-TR']

if __name__ == "__main__":
    import time
    import sys
    
    raw_input("Press the 'sync' button on the back of your Wiimote Plus " +
              "or buttons (1) and (2) on your classic Wiimote.\n" +
              "Press <return> once the Wiimote's LEDs start blinking.")

    if len(sys.argv) == 1:
        addr, name = find()[0]
    elif len(sys.argv) == 2:
        addr = sys.argv[1]
        name = None
    elif len(sys.argv) == 3:
        addr, name = sys.argv[1:3]
    print("Connecting to %s (%s)" % (name, addr))
    wm = connect(addr, name)

    while True:
        if wm.buttons["A"]:
            wm.leds[0] = True
            wm.rumble(0.1)
            print(wm.accelerometer)
        else:
            wm.leds[0] = False
            pass
        time.sleep(0.05)

