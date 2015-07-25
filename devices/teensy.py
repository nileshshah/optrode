#!/usr/bin/env python
import os, sys, time, re

import numpy as np

from serial_devices import Serial_Device

class Teensy31(Serial_Device):
    port_name = 'Teensy' #on windows at least
    name = 'Teensy 3.1'
    def __init__(self, *args, **kw):
        super(Teensy31,self).__init__(self.port_name,self.name, **kw)
        
        ## parameters for blocking read
        #self.block_size = 4096 # could be platform dependent
        #self.ser.timeout = 1.0  # may need to modify based on computer
        
    def send(self,arr):
        arr = map(int,arr)
        dat = bytearray(arr)
        self.ser.write(dat)
        self.ser.flushOutput()
    
    def read(self):
        ## blocking read
        #try:
        #    x = self.ser.read(self.block_size)
        #    return len(x),x
        #except:
        #    return (0,[])
        
        bytesToRead = self.ser.inWaiting()
        if (bytesToRead > 0):
            return bytesToRead, self.ser.read(bytesToRead)
        else:
            return (0,[])
        
    def start(self):
        self.send([1])
        self.log('start acquisition')
        
    def resume(self):
        self.send([4])
        self.log('resume acquisition')
        
    def stop(self):
        self.send([2])
        self.log('stop acquisition')
        
    def pause(self):
        self.send([3])
        self.log('pause acquisition')
        

if __name__ == '__main__':
    pass