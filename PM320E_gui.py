#!/usr/bin/env python
import os, sys, time, re

import numpy as np

from PySide import QtGui, QtCore
import pyqtgraph as pg

from PM320E import PM320E

from device_procs import Raw_Data_CSV_Export_Process,\
                         Device_Acquisition_Process, Device

from device_procs_gui import Acquisition_Control, Save_Raw_Data_Control,\
                            Save_Snapshot_Control

from multi_XY_plots import XY_Plot_Data, XY_Line_Plots, X_Window_Control

import multiprocessing
import Queue #needed separately for the Empty exception
DEBUG = False

class PM_Process(Device_Acquisition_Process):
    device = PM320E
    name = 'Power Meter Process'
    data_fields = ['Time','Power (W)']
    def __init__(self):
        super(PM_Process,self).__init__(input_q_size=2,\
                                        output_q_size=2,\
                                        acq_stats_q_size=None,\
                                        raw_data_export_q_size=2)

        self.raw_data = []
        self.samples = []
        
    def _run(self):
        self.init_device()
        self.pm = self.device
        self.device.set_range(1,'R10MW')
        self.device.set_wl(1,808)
        self.t0 = time.clock()
        
        while not self.exit.is_set():
            
            cmd,value = self.process_input()
            if cmd:
                if cmd == 'on':
                    self.awake = True
                elif cmd == 'off':
                    self.awake = False
                    #print 'off'
                elif cmd == 'wavelength':
                    self.pm.set_wl(1,int(value))
                elif cmd == 'range':
                    self.pm.set_range(1,str(value))
            
            if self.awake:
                pw = self.pm.get_power(1,n_pts=1,is_ave=False)[0]
                if pw > 0.000001:
                    t = time.clock() - self.t0
                    self.samples.append((t,pw))
                    self.raw_data.append([t,pw])
                
                if self.send_data(self.output_q,self.samples,1):
                    self.samples = []
                        
                if self.send_data(self.raw_export_q,self.raw_data,1):
                    self.raw_data = []
        
        if self.pm:
            self.pm.close()

    def run(self):
        self._run()
        
class PM_Device(Device):
    def __init__(self):
        super(PM_Device,self).__init__()
        self.name = 'PM'
        self.acq = PM_Process()
        self.add_proc(self.acq)
        
        self.raw_export = Raw_Data_CSV_Export_Process(self.acq,fmt="%f")
        self.add_proc(self.raw_export)

        self.buffer = PM_Buffer(self.acq.output_q)

class PM_Buffer(object):
    def __init__(self,data_q):
        self.data_q = data_q
        self.data_buffersize = 100000
        
        self.data_dtype = np.dtype([('tstamp','f4'),('pw','f4')])
        
        self.data = np.zeros((self.data_buffersize,),dtype=self.data_dtype)
    
    def update_data(self):
        try:
            new_data = self.data_q.get(False)
        except Queue.Empty:
            new_data = None
        if type(new_data) == list:
            in_data = np.array(new_data,dtype=self.data_dtype)
            n = len(in_data)
            if n > 0:
                self.data[:-n] = self.data[n:]
            self.data[-n:] = in_data
            
    def get_data_t_window_idx(self,t_window):
        t_end = self.data['tstamp'][-1]
        t_start = t_end - t_window
        idx = (np.abs(self.data['tstamp']-t_start)).argmin()
        return idx

class Wavelength_Control(QtGui.QWidget):
    def __init__(self,pm):
        super(Wavelength_Control,self).__init__()
        
        self.pm = pm
        self.wl = 808
        self.set_wl_button = QtGui.QPushButton('Set Wavelength',self)
        self.set_wl_button.clicked.connect(self.set_wl)
        self.wl_label = QtGui.QLabel(str(self.wl))
        
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.set_wl_button)
        layout.addWidget(self.wl_label)
        self.setLayout(layout)
    
    def set_wl(self):
        wl_int,ok = QtGui.QInputDialog.getInt(self, u'Power Meter',\
                                              u'Set Wavelength (nm)',\
                                              value=self.wl,\
                                              min=300, max=1000)
        if ok:
            self.wl_label.setText(str(wl_int))
            self.wl = wl_int
            try:
                self.pm.acq.input_q.put('wavelength:%d' %wl_int)
            except Queue.Full:
                print 'Command Queue Full'
                pass
    
class PM_Raw_Data_Monitor(QtGui.QWidget):
    def __init__(self, pm,parent=None):
        #super(PM_Raw_Data_Monitor, self).__init__()
        QtGui.QWidget.__init__(self,parent=parent)        
        self.pm = pm
        
        self.plots = []
        
        self.raw_data_plot = XY_Line_Plots(parent=self)
        self.raw_data_plot.enableAutoRange(axis='y')
        self.raw_data_plot.setMouseEnabled(x=False,y=False)
        self.plots.append(self.raw_data_plot)
        
        self.raw_data_plot.setLabel('left', 'Power', units='W')
        self.raw_data_plot.setLabel('bottom', 'Time', units='s')
        
        self.raw_data_plot.add_data(PM_Raw_Data(self.raw_data_plot,\
                                                self.pm.buffer,\
                                                label='Power',\
                                                name='Power'))
        self.raw_data_plot.xydatas[-1].add_plot(color='r')
        
        self.acq_control = Acquisition_Control(self.pm,self.plots,parent=self)
        
        self.raw_data_control = Save_Raw_Data_Control(self.pm.raw_export.param_q,\
                                                      self.acq_control)
        self.snapshot_control = Save_Snapshot_Control(self.raw_data_plot,\
                                                      self.acq_control)
        
        self.wavelength_control = Wavelength_Control(self.pm)
        
        right_side_layout = QtGui.QVBoxLayout()
        right_side_layout.addWidget(self.acq_control)
        right_side_layout.addWidget(self.wavelength_control)
        right_side_layout.addWidget(self.raw_data_control)
        right_side_layout.addWidget(self.snapshot_control)
        right_side_layout.addStretch()
        
        raw_data_layout = QtGui.QHBoxLayout()
        raw_data_layout.addWidget(self.raw_data_plot,1)
        raw_data_layout.addLayout(right_side_layout)
        
        self.setLayout(raw_data_layout)
        
        self.update_t_draw = QtCore.QTimer()
        self.update_t_draw.timeout.connect(self.update_plot)
        self.update_t_draw.start(200)
        
        self.update_t_data = QtCore.QTimer()
        self.update_t_data.timeout.connect(self.update_data)
        self.update_t_data.start(100)
        
    def update_data(self):
        self.pm.buffer.update_data()
        
    def update_plot(self):
        self.raw_data_plot.update_plots()
        
class PM_Raw_Data(XY_Plot_Data):
    def __init__(self,parent_plot, data_buffer, label='',name=''):
        super(PM_Raw_Data,self).__init__(parent_plot,label, name)
        self.buffer = data_buffer
    
    def get_xy(self):
        idx = self.buffer.get_data_t_window_idx(self.x_window)
        t_end = self.buffer.data['tstamp'][-1]
        new_tstamp = self.buffer.data['tstamp'][idx:] - t_end
        new_data = self.buffer.data['pw'][idx:]
        #print min(new_tstamp),max(new_tstamp),min(new_data),max(new_data)
        return new_tstamp, new_data
    
class PM_Monitor(QtGui.QWidget):
    def __init__(self,parent):
        #super(PM_Monitor, self).__init__()
        QtGui.QWidget.__init__(self,parent=parent)        
        self.pm = PM_Device()
        self.pm.start()
            
        self.raw_data_monitor = PM_Raw_Data_Monitor(self.pm,parent=self)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.raw_data_monitor)
        self.setLayout(layout)

    def shutdown(self):
        self.pm.shutdown()
        
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    widget = PM_Monitor()
    app.aboutToQuit.connect(widget.shutdown)
    widget.resize(1200,768)
    widget.show()
    sys.exit(app.exec_())
    