#!/usr/bin/env python
import os, sys, time, csv

import numpy as np

from PySide import QtGui, QtCore
import pyqtgraph as pg

from teensy_process import Teensy_Device, Teensy_Plot_Raw_Data

from gui.device_procs_gui import Acquisition_Control, Save_Raw_Data_Control, \
                                  Transfer_Status_Plots, Save_Snapshot_Control

from gui.multi_XY_plots import XY_Line_Plots, Plot_Checkboxes_2D, \
                           Plot_Checkboxes_Column, X_Window_Control

class Raw_Data_Monitor(QtGui.QWidget):
    def __init__(self,optrode,parent=None):
        #super(Raw_Data_Monitor, self).__init__()
        QtGui.QWidget.__init__(self,parent=parent)        
        self.optrode = optrode

        self.plots = []
        
        self.raw_data_plot = XY_Line_Plots(parent=self)
        self.raw_data_plot.setYRange(0,4096)
        self.raw_data_plot.setLimits(yMin=0,yMax=4096,maxYRange=4096,minYRange=0)
        self.plots.append(self.raw_data_plot)
        
        n_items = len(self.optrode.buffer.lasers)*len(self.optrode.buffer.ai_channels)
        initial_colors = iter([pg.colorStr(pg.intColor(i,values=n_items)) \
                               for i in range(n_items)])
        
        chkbox_columns = []
        for laser in self.optrode.buffer.lasers:
            chkbox_columns.append(Plot_Checkboxes_Column(initial_colors,col_label = str(laser)))
            for channel in self.optrode.buffer.ai_channels:
                self.raw_data_plot.add_data(Teensy_Plot_Raw_Data(self.raw_data_plot,\
                                                                 self.optrode.buffer,\
                                                                 laser, channel,\
                                                                 label = channel,\
                                                                 name = '_'.join([laser,channel])))
                chkbox_columns[-1].add_row(self.raw_data_plot.xydatas[-1])
            chkbox_columns[-1].finalize_layout()
            
        self.checkboxes = Plot_Checkboxes_2D(chkbox_columns)

        
        
        self.transfer_stats_plots = Transfer_Status_Plots(self.optrode.buffer,\
                    {'byte_count': {'x':0,'y':0,'title':'byte count per block',\
                                    'left': ('bytes')},\
                     'line_count': {'x':0, 'y':1, 'title':'sample count per block',\
                                    'left': ('samples')},\
                     'dt': {'x':0, 'y':2, 'title':'acquisition time per block',\
                                  'left': ('acq time','s')},\
                     'tx_rate': {'x':0, 'y':3, 'title':'data transfer rate',\
                                 'left':('Mbits/s')},\
                     'smpl_rate': {'x':0,'y':4, 'title':'data sampling rate',\
                                   'left':('kHz')}})
        
        self.plots.append(self.transfer_stats_plots)

        self.acq_control = Acquisition_Control(self.optrode,self.plots,parent=self)  
        
        self.raw_data_control = Save_Raw_Data_Control(self.optrode.raw_export.param_q,\
                                                      self.acq_control)
        self.snapshot_control = Save_Snapshot_Control(self.raw_data_plot,\
                                                      self.acq_control)
        
        right_side_layout = QtGui.QVBoxLayout()
        right_side_layout.addWidget(self.acq_control)
        right_side_layout.addWidget(self.checkboxes)
        right_side_layout.addWidget(self.raw_data_control)
        right_side_layout.addWidget(self.snapshot_control)
        
        raw_data_layout = QtGui.QHBoxLayout()
        raw_data_layout.addWidget(self.raw_data_plot,1)
        raw_data_layout.addLayout(right_side_layout)
        
        layout = QtGui.QVBoxLayout()
        layout.addLayout(raw_data_layout,2)
        layout.addWidget(self.transfer_stats_plots,1)
        self.setLayout(layout)
    
        self.t_optrode_data = QtCore.QTimer()
        self.t_optrode_data.timeout.connect(self.update_optrode_data)
        self.t_optrode_data.start(50) # ms
        
        self.t_optrode_stats = QtCore.QTimer()
        self.t_optrode_stats.timeout.connect(self.update_optrode_stats)
        self.t_optrode_stats.start(500) # ms

        self.t_optrode_tx_plots = QtCore.QTimer()
        self.t_optrode_tx_plots.timeout.connect(self.update_optrode_tx_plots)
        self.t_optrode_tx_plots.start(500) #ms

        self.t_optrode_data_plots = QtCore.QTimer()
        self.t_optrode_data_plots.timeout.connect(self.update_optrode_data_plots)
        self.t_optrode_data_plots.start(200) #ms
    
    def update_optrode_data(self):
        self.optrode.buffer.update_data()
    
    def update_optrode_stats(self):
        self.optrode.buffer.update_stats()
    
    def update_optrode_tx_plots(self):
        self.transfer_stats_plots.update_plots()
    
    def update_optrode_data_plots(self):
        self.raw_data_plot.update_plots()
        
class Optrode_Monitor(QtGui.QWidget):
    def __init__(self,parent=None):
        #super(Optrode_Monitor, self).__init__()
        QtGui.QWidget.__init__(self,parent=parent)        
        self.optrode = Teensy_Device()
        self.optrode.start()
        
        self.raw_data_monitor = Raw_Data_Monitor(self.optrode,parent=self)
        if parent == None:
            self.time_control = X_Window_Control()
            self.time_control.add_plots(self.raw_data_monitor.plots)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.raw_data_monitor)
        if parent == None:
            layout.addWidget(self.time_control)
        self.setLayout(layout)
        
    def shutdown(self):
        self.optrode.shutdown()

    
if __name__ == '__main__':
    import cProfile
    app = QtGui.QApplication(sys.argv)
    widget = Optrode_Monitor()
    app.aboutToQuit.connect(widget.shutdown)
    widget.resize(1024,768)
    widget.show()
    sys.exit(app.exec_())
    