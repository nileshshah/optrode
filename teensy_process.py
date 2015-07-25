#!/usr/bin/env python

import os, sys, time, re

import numpy as np

from devices.teensy import Teensy31

from debug_tools import timer_loop, timer_dt, q_send, q_get
from devices.device_procs import Raw_Data_CSV_Export_Process,\
                                 Device_Acquisition_Process, Device

from gui.multi_XY_plots import XY_Plot_Data
import multiprocessing
import Queue #needed separately for the Empty exception

DEBUG_T = False

class Teensy_Process(Device_Acquisition_Process):
    device = Teensy31
    name = 'Teensy Process'
    data_fields = ['Time', 'PD1', 'PD2', 'PD3', 'MPD1', 'MPD2', 'laserID']
    def __init__(self):
        #Device_Acquisition_Process.__init__(self,*args,**kw)
        super(Teensy_Process,self).__init__(input_q_size=2,\
                                            output_q_size=2,\
                                            acq_stats_q_size=2,\
                                            raw_data_export_q_size=2)
                
        self.first_on = False
        
        parse_string = ''.join(['\n'])+'(.{15})'+''.join(['\n'])
        self.line_pat = re.compile(parse_string,re.DOTALL)
        
        self.acq_stats = []
        self.samples = []
        self.raw_data = []
        
        
        self.sample_dtype = [('tstamp','<l'),\
                            ('PD1','>H'),\
                            ('PD2', '>H'),\
                            ('PD3', '>H'),\
                            ('MPD1','>H'),\
                            ('MPD2', '>H'),\
                            ('laserID','B')]
        
    def run(self):
        self.init_device()
        
        #print 'shoo'
        
        t_run_loop = timer_loop('run loop')
        t_read = timer_loop('read data')
        t_acq_stats = timer_dt('acq stats')
        t_valid = timer_loop('valid lines')
        t_parse = timer_loop('parse lines')
        t_add = timer_loop('buffer add')
        t_input = timer_dt('command check',target_dt=1.0)

        #print 'boo'
        
        n=0
        
        while not self.exit.is_set():      
            t_run_loop.begin()
            
            if t_input.check():
                cmd,value = self.process_input()
                if cmd:
                    #print 'in process',cmd, self.device
                    if cmd == 'on':
                        if self.first_on:
                            #print 'resume', self.device
                            self.device.resume()
                        else:
                            #print 'start',self.device
                            self.device.start()
                            self.first_on = True
                    elif cmd == 'off':
                        if self.first_on:
                            self.device.pause()
                        else:
                            self.device.stop()

            
            t_read.begin()
            byte_cnt, chunk = self.device.read()
            
            if byte_cnt > 0:
                t_read.end()
                
                t_valid.begin()
                str_lines = re.findall(self.line_pat, chunk)
                t_valid.end()
                
                t_parse.begin()
                items = np.array(str_lines,dtype=self.sample_dtype)
                line_cnt = items.size
                if line_cnt > 0:
                    t_parse.end()
                    self.acq_stats.append((byte_cnt,line_cnt,t_acq_stats.dt,t_acq_stats.t))
                    
                    if len(self.samples) > 0:
                        t_add.begin()
                        self.samples = np.hstack((self.samples,items))
                        t_add.end()
                    else:
                        self.samples = items
                    
                    self.raw_data.append(items)
                    
            if self.send_data(self.output_q,self.samples,1):
                self.samples = []
            
            if self.send_data(self.acq_stats_q,self.acq_stats,1):
                self.acq_stats = []
            
            if self.send_data(self.raw_export_q,self.raw_data,1):
                self.raw_data = []
                            
            t_run_loop.end()
            
        self.close_device()
        
        if DEBUG_T:
            self.log(t_run_loop)
            self.log(t_read)
            self.log(t_valid)
            self.log(t_parse)
            self.log(t_add)

class Teensy_Data_Buffer(object):
    def __init__(self, data_q, stats_q):
        self.data_q = data_q
        self.stats_q = stats_q
        self.data_buffersize = 200000
        self.stats_buffersize = 20000
        
        self.ai_channels = ['PD1', 'PD2', 'PD3', 'MPD1', 'MPD2']
        self.lasers = ['808','850']
        
        self.data_dtype = np.dtype([('tstamp','<l'),\
                            ('PD1','>H'),\
                            ('PD2', '>H'),\
                            ('PD3', '>H'),\
                            ('MPD1','>H'),\
                            ('MPD2', '>H'),\
                            ('laserID','>H')])
        
        self.instats_dtype= np.dtype([('byte_count','i2'),\
                   ('line_count','i2'),\
                   ('dt','f4'),\
                   ('t','f4')])
        
        self.stats_dtype= np.dtype([('byte_count','i2'),\
                   ('line_count','i2'),\
                   ('dt','f4'),\
                   ('t','f4'),\
                   ('tx_rate','f4'),\
                   ('smpl_rate','f4')])
        
        self.data = {}
        buffsize = self.data_buffersize
        for k in ['808','850']:
            self.data[k] = {}
            self.data[k]['tstamp'] = np.zeros((buffsize,),dtype=np.float32)
            self.data[k]['PD1'] = np.zeros((buffsize,),dtype=np.float32)
            self.data[k]['PD2'] = np.zeros((buffsize,),dtype=np.float32)
            self.data[k]['PD3'] = np.zeros((buffsize,),dtype=np.float32)
            self.data[k]['MPD1'] = np.zeros((buffsize,),dtype=np.float32)
            self.data[k]['MPD2'] = np.zeros((buffsize,),dtype=np.float32)
        self.stats = np.zeros((self.data_buffersize),dtype=self.stats_dtype)
        self.t_data_update = timer_loop('data update')
        
    def update_data(self):
        self.t_data_update.begin()
        try:
            new_data = self.data_q.get(False)
        except Queue.Empty:
            new_data = None        
        if type(new_data) == np.ndarray:
            n = len(new_data)
            if n > 0:
                for i,lsr in enumerate(['808','850']):
                    which = np.where(new_data['laserID'] == i)[0]
                    n_lsr = len(which)
                    for k in self.data[lsr].keys():
                        self.data[lsr][k][:-n_lsr] = self.data[lsr][k][n_lsr:]
                        self.data[lsr][k][-n_lsr:] = new_data[k][which] * 1.0
                    self.data[lsr]['tstamp'][-n_lsr:] /= 1.0e6
            self.t_data_update.end()
            return new_data['tstamp'][-1], new_data['tstamp'][0],new_data.size, n
        return None
        
    def update_stats(self):
        try:
            new_stats = self.stats_q.get(False)
        except Queue.Empty:
            new_stats  = None
        
        if type(new_stats) == list:
            n = len(new_stats)
            if n > 0:
                #self.stats = np.roll(self.stats,-n)
                self.stats[:-n] = self.stats[n:]
                in_stats = np.array(new_stats,dtype=self.instats_dtype)
                self.stats['byte_count'][-n:] = in_stats['byte_count']
                self.stats['line_count'][-n:] = in_stats['line_count']
                self.stats['dt'][-n:] = in_stats['dt'] * 1.0
                self.stats['t'][-n:] = in_stats['t'] * 1.0
                self.stats['tx_rate'][-n:] = (self.stats['byte_count'][-n:] * 8.) / \
                                             self.stats['dt'][-n:] / 1e6 #Mbits/sec
                self.stats['smpl_rate'][-n:] = self.stats['line_count'][-n:]/ \
                                             self.stats['dt'][-n:] / 1000 # kHz
                return n
        return None

    def get_data_t_window_idx(self,t_window):
        t_end = self.data['808']['tstamp'][-1]
        t_start = t_end - t_window
        idx = (np.abs(self.data['808']['tstamp']-t_start)).argmin()
        return idx
        #est_idx = int(self.stats['smpl_rate'][-1]*t_window*1000/2.0)
        #return -est_idx
        
    
    def get_stat_t_window_idx(self,t_window):
        t_end = self.stats['t'][-1]
        t_start = t_end - t_window
        idx = (np.abs(self.stats['t']-t_start)).argmin()
        return idx
    
class Teensy_Plot_Raw_Data(XY_Plot_Data):
    def __init__(self,parent_plot, data_buffer, laser, channel,label='',name=''):
        super(Teensy_Plot_Raw_Data,self).__init__(parent_plot,label, name)
        self.buff = data_buffer
        self.laser = laser
        self.channel = channel
    
    def get_xy(self):
        est_idx = self.buff.get_data_t_window_idx(self.x_window)
        t_end = self.buff.data[self.laser]['tstamp'][-1]
        return self.buff.data[self.laser]['tstamp'][est_idx:] - t_end,\
               self.buff.data[self.laser][self.channel][est_idx:]

#class Teensy_Plot_Proc_Data(XY_Plot_Data):
#    def __init__(self,data_buffer,key):
#        super(Teensy_Plot_Proc_Data,self).__init__()
#

class Teensy_Device(Device):
    def __init__(self):
        super(Teensy_Device,self).__init__()
        self.name = 'teensy'
        self.acq = Teensy_Process()
        self.add_proc(self.acq)
        
        self.raw_export = Raw_Data_CSV_Export_Process(self.acq)
        self.add_proc(self.raw_export)

        self.buffer = Teensy_Data_Buffer(self.acq.output_q,self.acq.acq_stats_q)
        
        
if __name__ == '__main__':
    optrode = Teensy_Device()
    buff = Teensy_Data_Buffer(optrode.acq.output_q,optrode.acq.acq_stats_q)
    optrode.start()
    time.sleep(5)
    q_send(optrode.acq.input_q,'off',n=1,delay=0.3)
    q_send(optrode.acq.input_q,'on',n=1,delay=0.3)
    q_send(optrode.raw_export.param_q,'file:test.csv')
    q_send(optrode.raw_export.param_q,'start')
    import matplotlib.pyplot as plt   
    
    t_try_q_get = timer_dt('main: try q get',target_dt=0.1)
    t_while_loop = timer_loop('main: while')
    t_parse_loop = timer_loop('main: parse')
    
    #data = []
    #stats = []
    block_start_t = []
    block_end_t = []
    block_sizes = []
    n_data = 0
    n_stats = 0
    
    t_while_loop.begin()
    while t_while_loop.total_time < 10.0:
        t_while_loop.begin()
        
        if t_try_q_get.check():
            print t_try_q_get.n
            
            t_parse_loop.begin()
            result = buff.update_data()
            if result:
                t_end,t_start,block_size, n = result
                block_start_t.append(t_start)
                block_end_t.append(t_end)
                block_sizes.append(block_size)
                t_parse_loop.end()
                n_data += n
                
            n = buff.update_stats()
            if n:
                n_stats += n
        
        t_while_loop.end()
        
    q_send(optrode.acq.input_q,'off',n=2,delay=0.3)
    q_send(optrode.raw_export.param_q,'stop')
    optrode.shutdown()
    
    print 'main while loop - N: %d' %t_while_loop.n
    print '# attempts to read from queue:',t_try_q_get.n
    print 'data parse and append loop - N: %d, avg time: %.3e' \
            %(t_parse_loop.n, t_parse_loop.avg_loop_time)
    print 'total samples read',n_data
    #if n_data < 200000:
    #    buff.data = buff.data[-n_data:]
    if n_stats < 20000:
        buff.stats = buff.stats[-n_stats:]

    plt.plot(buff.stats['t'],buff.stats['smpl_rate'])
    plt.title('Sampling Rate - kHz')
    plt.show()
    print 'median sampling rate',np.median(buff.stats['smpl_rate'])
    
    plt.plot(buff.stats['t'],buff.stats['line_count'])
    plt.title('Samples per block')
    plt.show()

    plt.plot(buff.stats['t'],buff.stats['byte_count'])
    plt.title('serial read block size')
    plt.show()
        
    y0 = np.array(block_start_t)/1.0e6
    y1 = np.array(block_end_t)/1.0e6
    y = np.diff(y0)
    x = range(len(y))
    plt.plot(x,y)
    plt.title('dt (s) between each block (process) read from output_q')
    plt.show()
    
    x = range(len(block_sizes))
    plt.plot(x,block_sizes)
    plt.title('number of samples in each block (process)')
    plt.show()
        
    x = buff.data['808']['tstamp']*1.0e3
    y = np.diff(x)
    plt.plot(x[1:],y)
    plt.title('dt (ms) between samples, 808nm')
    plt.show()
    
    t = []
    raw_file = open('test.csv','r')
    raw_file.readline() # skip header line
    for line in raw_file:
        items = line.split(',')
        t.append(long(items[0]))
    t = np.array(t)
    dt = np.diff(t)
    plt.plot(dt)
    plt.title('dt (us) between samples in raw data file')
    plt.show()
    raw_file.close()
