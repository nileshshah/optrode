#!/usr/bin/env python
import time, sys, os, StringIO
import multiprocessing
import Queue #needed separately for the Empty exception
import cProfile

import numpy as np

DEBUG_Q = False
DEBUG_PROCESS = False

'''
## data_input_q

#class Data(object):
#    def __init__(self):
#        self.reset()
#    def reset(self):
#        self.data = []
#    def __lshift__(self,new_data):
#        self.data.append(new_data)
#    def __call__(self):
#        return self.data

class Data_Input_Queue(object):
    def __init__(self,maxsize=2,blocking=True,timeout=1.0):
        self.q = multiprocessing.Queue(maxsize=maxsize)
        self.blocking = blocking
        self.timeout = timeout
        self.data = []
        
    def receive(self):
        try:
            self.process_incoming(self.q.get(self.blocking,self.timeout))
        except Queue.Empty:
            pass
        
    def __rshift__(self,target):
        try:
            target << self.process_outgoing()
            self.data = []
        except:
            pass
    
    def reset(self):
        self.data = []
    
    def process_incoming(self,new_data):
        self.data.append(new_data)
    
    def process_outgoing(self):
        return self.data
    
class Data_Output_Queue(object):
    def __init__(self,maxsize=2,blocking=False,timeout=None,min_length=1):
        self.q = multiprocessing.Queue(maxsize=maxsize)
        self.blocking = blocking
        self.timeout = timeout
        self.min_length = min_length
        self.data = []
        
    def send(self):
        if len(self.data) > self.min_length:
            try:
                self.q.put(self.process_outgoing(),self.blocking,self.timeout)
                self.data = []
            except Queue.Full:
                pass
    
    def __lshift__(self,new_data):
        self.process_incoming(new_data)

    def reset(self):
        self.data = []
    
    def process_incoming(self,new_data):
        self.data.append(new_data)
    
    def process_outgoing(self):
        return self.data
    
class Process_Cmd_Queue(object):
    def __init__(self,maxsize=2,blocking=False,timeout=None):
        self.q = multiprocessing.Queue(maxsize=maxsize)
        self.blocking = blocking
        self.timeout = timeout
        self.cmd = None
        self.value = None
        
    def receive(self):
        cmd_string = None
        cmd = None
        value = None
        try:
            cmd_string = self.q.get(self.blocking,self.timeout)
        except Queue.Empty:
            return False
        
        if ((type(cmd_string) == str) or (type(cmd_string) == unicode)):
            delimiter_idx = cmd_string.find(':')
            if delimiter_idx > 0:
                cmd = cmd_string[:delimiter_idx]
                value = cmd_string[delimiter_idx+1:]
            elif delimiter_idx == -1:
                cmd = cmd_string
                value = None
        
        self.cmd = cmd
        self.value = value

        if cmd:
            return True
        else:
            return False
    
    def get_cmd(self):
        return self.cmd,self.value
    
class Processor(multiprocessing.Process):
    def __init(self,**kw):
        multiprocessing.Process.__init__(self)
        self.exit = multiprocessing.Event()
        self.exit.clear()
        self.active = multiprocessing.Event()
        self.active.clear()
        if 'profile_filename' in kw:
            self.profile_filename = kw['profile_filename']
        else:
            self.profile_filename = None
            
    def shutdown(self):
        self.exit.set()
        time.sleep(1.0)
        
    def run(self):
        if self.profile_filename:
            cProfile.runctx("self._run()",globals(),locals()\
                            ,self.profile_filename)
        else:
            self._run()
    
    def _run(self):
        self.init_run()
        
        while not self.exit.is_set():
            if self.active.is_set():
                self.run_loop()
        
        self.close_run()
    
    def init_run(self):
        pass
    
    def run_loop(self):
        pass
    
    def close_run(self):
        pass

class Data_Export_Process(Processor):
    def __init__(self,input_q,cmd_q, **kw):

class Data_Export_Process(multiprocessing.Process):
    def __init__(self, data_input_q):
        multiprocessing.Process.__init__(self)
        self.input_q = input_q
        self.cmd_q = multiprocessing.Queue(maxsize=2)
        
        self.exit = multiprocessing.Event()
        self.exit.clear()
        
        self.active = multiprocessing.Event()
        self.save.clear()
        
        self.export_filename = None

'''

class Raw_Data_CSV_Export_Process(multiprocessing.Process):
    def __init__(self, data_acq_process, fmt='%d'):
        multiprocessing.Process.__init__(self)
        acq_proc = data_acq_process
        
        self.export_q = acq_proc.raw_export_q
        self.param_q = multiprocessing.Queue(maxsize=2)
        self.data_fields = acq_proc.data_fields
        
        self.exit = multiprocessing.Event()
        self.exit.clear()
        
        self.raw_data_file = None
        self.save_raw = False
        self.fmt = fmt
        
    def shutdown(self):
        self.exit.set()
        time.sleep(1.0)
    
    def close(self):
        if self.raw_data_file:
            self.raw_data_file.close()
    
    def new_raw_data_file(self, filename):
        if self.raw_data_file:
            self.raw_data_file.close()
        self.raw_data_file = open(filename,'wb')
        self.raw_data_file.write(','.join(self.data_fields)+'\n')
    
    def process_input(self):
        cmd_string = None
        try:
            cmd_string = self.param_q.get(False)
        except Queue.Empty:
            pass
        
        if (type(cmd_string) == str) or (type(cmd_string) == unicode):
            delimiter_idx = cmd_string.find(':')
            if delimiter_idx > 0:
                cmd = cmd_string[:delimiter_idx]
                value = cmd_string[delimiter_idx+1:]
                if cmd == 'file':
                    self.new_raw_data_file(value)
                elif cmd == 'comment':
                    if self.raw_data_file:
                        self.raw_data_file.write(value+'\n')        
            elif delimiter_idx == -1:
                cmd = cmd_string
                if cmd == 'start':
                    self.save_raw = True
                if cmd == 'stop':
                    self.save_raw = False                        
    
    def run(self):
        cProfile.runctx("self._run()",globals(),locals(),"raw_data_stats")
        
    def _run(self):
        
        t0 = time.time()
        t_prev = time.time()-t0
        while not self.exit.is_set():            
            
            t = time.time() - t0
            if t-t_prev > 0.1:
                self.process_input()
                t_prev = t
            else:
                pass
            
            if self.save_raw and self.raw_data_file:
                items = None
                try:
                    #items = self.export_q.get(False)
                    items = self.export_q.get(True,1.0)
                except: 
                    pass
                if type(items) == list:
                    out = StringIO.StringIO()
                    for item in items:
                        np.savetxt(out,item,self.fmt,delimiter=',')
                    self.raw_data_file.write(out.getvalue())
                    out.close()
            #else:
            #    time.sleep(1.0)

        self.close()
        
class Device_Acquisition_Process(multiprocessing.Process):
    #device = None
    #name = ''
    def __init__(self, input_q_size=1,output_q_size=1,acq_stats_q_size=1,\
                 raw_data_export_q_size=None):
        #multiprocessing.Process.__init__(self)
        super(Device_Acquisition_Process, self).__init__()
        
        self.input_q = multiprocessing.Queue(maxsize=input_q_size)
        self.output_q = multiprocessing.Queue(maxsize=output_q_size)
        if acq_stats_q_size:
            self.acq_stats_q =  multiprocessing.Queue(maxsize=acq_stats_q_size)
        if raw_data_export_q_size:
            self.raw_export_q = multiprocessing.Queue(maxsize=raw_data_export_q_size)
        self.exit = multiprocessing.Event()
        self.exit.clear()
        
        self.awake = False
    
    def log(self,text):
        if DEBUG_PROCESS:
            print '%s: %s' %(self.name,text)
            sys.stdout.flush()
            
    def shutdown(self):
        self.exit.set()
        time.sleep(1.0)  # if too short, won't run any code outside while loop?
        self.log('shutting down')
    
    def init_device(self):
        try:
            self.device = self.device()
            print 'device: %s : found' %self.device.name
            sys.stdout.flush()
        except Exception, e:
            print 'problem connecting to device: ',e
            sys.stdout.flush()
            self.shutdown()

    def close_device(self):
        if self.device:
            try:
                self.device.stop()
                self.device.close()
            except:
                pass
    
    def process_input(self):
        try:
            cmd_string = self.input_q.get(False)
        except Queue.Empty:
            return (None,None)
        
        if type(cmd_string) == str:
            a = cmd_string.split(':')
            if len(a) > 1:
                cmd,value = a
            elif len(a) > 0:
                cmd = a[0]
                value = None
            return cmd,value
        else:
            return (None,None)
            
    def send_data(self,q,data,min_length):
        success = False
        if len(data) > min_length:
            try:
                q.put(data,False)
                success = True
            except Queue.Full:
                if DEBUG_Q:
                    print 'Output Queue Full'
        return success
    
    def run(self):
        pass
    
class Device(object):
    def __init__(self):
        self.procs = []
        self.active = False
        
    def shutdown(self):
        for proc in self.procs:
            try:
                proc.shutdown()
                time.sleep(1)
                proc.terminate()
            except:
                pass
    
    def sleep(self):
        for proc in self.procs:
            try:
                proc.sleep()
            except:
                pass
    
    def start(self):
        for proc in self.procs:
            proc.start()
    
    def add_proc(self,proc):
        self.procs.append(proc)


if __name__ == '__main__':
    pass
    #a = Processor('meow.txt')
    #a.start()
    #ime.sleep(1)
    #a.shutdown()
    
