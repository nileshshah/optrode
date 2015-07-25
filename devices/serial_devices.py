#!/usr/bin/env python
import time, os, sys

import serial
from serial.tools import list_ports

DEBUG_DEVICE = True

class Serial_Device(object):
    '''
    class for devices sending data through serial ports
    '''    
    def __init__(self,port_name,name,**kw):
        self.port = self.getPort(port_name)
        self.ser = serial.Serial(self.port[0], **kw)
        self.name = name            
        time.sleep(3) # wait for serial connection to establish
        
        self.flush()
        
    def close(self):
        self.ser.close()
    
    def flush(self):
        self.ser.flushInput()
        self.ser.flushOutput() 
    
    def getPort(self,port_name):
        """Discover device serial port"""
        ports_avaiable = list(list_ports.comports())
        device_port = None
        for port in ports_avaiable:
            if port[1].startswith(port_name):
                return port
    
    def log(self,text):
        if DEBUG_DEVICE:
            print self.name,text
    
    def close(self):
        self.ser.close()
