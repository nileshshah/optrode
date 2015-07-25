#!/usr/bin/env python
import os,sys

import numpy as np

from PySide import QtGui, QtCore

import pyqtgraph as pg

import Queue #needed separately for the Empty exception

class Acquisition_Control(QtGui.QWidget):
    def __init__(self,device,plots=[],parent=None):
        #super(Acquisition_Control,self).__init__(parent=parent)
        QtGui.QWidget.__init__(self,parent=parent)
        
        self.device = device
        if type(plots) == list:
            self.plots = plots
        else:
            self.plots = [plots]
        self.process_input_queue = device.acq.input_q
        
        self.acq_button = QtGui.QPushButton('Start/Stop',self)
        self.acq_button.clicked.connect(self.switch_acquisition)

        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.acq_button)
        self.setLayout(layout)
    
        self.set_off()
        
    def set_on(self):
        self.acq_button.setStyleSheet('QPushButton {background-color: green;}')
        try:
            self.process_input_queue.put('on',False)
            self.device.active = True
            for plot in self.plots:
                plot.set_active(self.device.active)
                #print plot,self.device.name,self.device.active
            #print
        except Queue.Full:
            print 'Acq Control - Command Queue Full?'
            pass
        
    def set_off(self):
        self.acq_button.setStyleSheet('QPushButton {background-color: red;}')
        try:
            self.process_input_queue.put('off',False)
            self.device.active = False
            #print self.device.name,self.device.active
            #print self.plots
            #print 
            for plot in self.plots:
                #print plot,self.device.name,self.device.active
                plot.set_active(self.device.active)
            #print
        except Queue.Full:
            print 'Acq Control - Command Queue Full?'
            pass
        
    def switch_acquisition(self):
        if self.device.active == False:
            self.set_on()
        elif self.device.active == True:
            self.set_off()
    
    @property
    def active(self):
        return self.device.active
            
class Save_Raw_Data_Control(QtGui.QWidget):
    def __init__(self, param_q,acq_control):
        super(Save_Raw_Data_Control,self).__init__()
        self.param_queue = param_q
        self.raw_data_file = ''
        self.save = False
        self.acq_control = acq_control
        
        self.raw_data_button = QtGui.QPushButton('Set Raw Data File')
        self.raw_data_label = QtGui.QLabel(self.raw_data_file)
        self.raw_data_label.setWordWrap(True)
        self.raw_data_button.clicked.connect(self.set_raw_data_file)
        
        self.raw_data_set_button = QtGui.QPushButton('Start/Stop',self)
        self.raw_data_set_button.clicked.connect(self.set_raw_data_acq)
        
        layout1 = QtGui.QHBoxLayout()
        layout1.addWidget(self.raw_data_button)
        layout1.addWidget(self.raw_data_set_button)
        
        layout = QtGui.QVBoxLayout()
        layout.addLayout(layout1)
        layout.addWidget(self.raw_data_label)
        
        self.setLayout(layout)
    
    def set_raw_data_acq(self):
        if self.raw_data_file:
            if self.save == False:
                self.save = True
                try:
                    self.param_queue.put('start',False)
                    self.raw_data_set_button.setStyleSheet('QPushButton {background-color: green;}')
                except Queue.Full:
                    print 'Command Queue Full'
                    pass
            elif self.save == True:
                self.save = False
                try:
                    self.param_queue.put('stop',False)
                    self.raw_data_set_button.setStyleSheet('QPushButton {background-color: red;}')
                except Queue.Full:
                    print 'Command Queue Full'
                    pass
            
    def set_raw_data_file(self):
        if self.acq_control.active:
            turn_on_later = True
            self.acq_control.set_off()
        else:
            turn_on_later = False
        fname = QtGui.QFileDialog.getSaveFileName(self,'Open File')
        if fname[0]:
            fname = fname[0]
            try:
                cmd = 'file:'+fname
                self.param_queue.put(cmd,False)
                self.raw_data_label.setText(fname)
                self.raw_data_file = fname
            except Queue.Full:
                print 'Command Queue Full'
                pass
        if turn_on_later:
            self.acq_control.set_on()
    
class Save_Snapshot_Control(QtGui.QWidget):
    def __init__(self, xy_plot, acq_control):
        super(Save_Snapshot_Control,self).__init__()
        
        self.xy_plot = xy_plot
        self.acq_control = acq_control
        
        self.snapshot_file = None
        
        self.set_file_button = QtGui.QPushButton('Set Snapshot File')
        self.file_label = QtGui.QLabel(self.snapshot_file)
        self.file_label.setWordWrap(True)
        self.set_file_button.clicked.connect(self.set_snapshot_file)
        
        self.save_button = QtGui.QPushButton('Save Snapshot',self)
        self.save_button.clicked.connect(self.save_snapshot)
        
        layout1 = QtGui.QHBoxLayout()
        layout1.addWidget(self.set_file_button)
        layout1.addWidget(self.save_button)
        
        layout = QtGui.QVBoxLayout()
        layout.addLayout(layout1)
        layout.addWidget(self.file_label)
        
        self.setLayout(layout)
    
    def set_snapshot_file(self):
        if self.acq_control.active:
            turn_on_later = True
            self.acq_control.set_off()
        else:
            turn_on_later = False
        fname = QtGui.QFileDialog.getSaveFileName(self,'Set Snapshot File')
        if fname[0]:
            fname = fname[0]
            self.snapshot_file = fname
            self.file_label.setText(fname)
        if turn_on_later:
            self.acq_control.set_on()
    
    def save_snapshot(self):
        if self.acq_control.active:
            turn_on_later = True
            self.acq_control.set_off()
        else:
            turn_on_later = False
        self.xy_plot.save_snapshot(self.snapshot_file)
        if turn_on_later:
            self.acq_control.set_on()           
        
class Transfer_Status_Plots(pg.GraphicsLayoutWidget):
    def __init__(self, buff, plot_dict,parent=None):
        #super(Transfer_Status_Plots, self).__init__(parent=parent)
        pg.GraphicsLayoutWidget.__init__(self,parent=parent)
        
        self.buffer = buff
        self.active = True
        
        self.x_window = 5.
                
        self._plots = {}
        
        for key, params in plot_dict.items():
            self._plots[key] = self.addPlot(params['x'], params['y'],\
                title = params['title'],\
                labels = {'bottom': ('time','s'), \
                          'left': params['left']}).plot(pen='r')
        
    def update_plots(self):
        if self.active:
            #try:
            #    self.buffer.update_acq_stats()
            #except Queue.Empty:
            #    pass
            idx = self.buffer.get_stat_t_window_idx(self.x_window)
            
            t = self.buffer.stats['t'][idx:]
            t = t - t[-1]
            
            for key, plot in self._plots.items():
                plot.setData(t,self.buffer.stats[key][idx:])
                
    def change_x_window(self, t):
        #if self.active:
        self.x_window = t

    def set_active(self,which):
        self.active = which        