# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:        ports.py
# Author:      Jan Kåre Vatne
# -------------------------------------------------------------------------------

import serial
from typing import Callable
import win32api
import win32con
import win32gui


class ComPorts(object):
    """
    Encapsules the COM ports. The application should create one object
    containing a list of COM-ports.  Calling scanConnections() will update
    the list and getAvailable() returns the list.
    """

    def __init__(self):
        self.available = []
        self.namelist = []
        self.scan_connections()

    def scan_connections(self):
        self.available = []
        self.namelist = []
        self.namelist.append("Select port...")
        for i in range(0, 255):
            try:
                s = serial.Serial("COM%d" % i)
                self.available.append((i, s.portstr))
                self.namelist.append(s.portstr)
                s.close()
            except serial.SerialException:
                pass
        return self.available

    def get_available(self):
        """ Returns the list of COM-ports found """
        return self.available

    def get_ports(self):
        """ Returns the list of COM-ports found """
        return self.namelist

    def get_default_port_no(self):
        """ Returns the last found COM-port number minus one.
        This is most likely the external USB module """
        if len(self.available) == 0:
            return None
        return self.available[len(self.available) - 1][0]

    def get_default_port_name(self):
        """ Returns the last found COM-port name.
        This is most likely the external USB module """
        if len(self.available) == 0:
            return ""
        return self.available[len(self.available) - 1][1]

    def port_no(self, name):
        i = 0
        for n in self.available:
            if n[1] == name:
                return n[0]
            i = i + 1


class DeviceListener:

    def __init__(self, on_change: Callable):
        self.on_change = on_change
        self._create_window()

    def _create_window(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._on_message
        wc.lpszClassName = self.__class__.__name__
        wc.hInstance = win32api.GetModuleHandle(None)
        class_atom = win32gui.RegisterClass(wc)
        return win32gui.CreateWindow(class_atom, self.__class__.__name__, 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)

    def _on_message(self, hwnd: int, msg: int, wparam: int, lparam: int):
        if msg == win32con.WM_DEVICECHANGE and wparam == 7:
            self.on_change()
        return 0

