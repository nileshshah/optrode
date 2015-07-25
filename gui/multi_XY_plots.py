#!/usr/bin/env python
import os, sys, csv
from itertools import izip_longest

import numpy as np

from PySide import QtGui, QtCore
import pyqtgraph as pg

from qtgui_util import QColorButton

class Plot_Checkbox(QtGui.QWidget):
    def __init__(self,plot_data):
        super(Plot_Checkbox, self).__init__()
        
        self.plot_data = plot_data
        self.label = self.plot_data.label
        
        self.checkbox = QtGui.QCheckBox('%s' %str(self.label),self)
        self.color_button = QColorButton(self)
        
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.color_button)
        hbox.addWidget(self.checkbox)
        self.setLayout(hbox)
    
        self.checkbox.stateChanged.connect(self.set_plot)
        self.color_button.colorChanged.connect(self.change_color)

    def set_plot(self):
        if self.checkbox.isChecked():
            self.plot_data.add_plot(self.color_button.color())
        else:
            self.plot_data.remove_plot()
    
    def change_color(self):
        self.plot_data.change_color(self.color_button.color())

    def setColor(self,color):
        self.color_button.setColor(color)

class Plot_Checkboxes_Column(QtGui.QWidget):
    def __init__(self, initial_colors, col_label = None):
        super(Plot_Checkboxes_Column,self).__init__()
        
        self.initial_colors = initial_colors
        self. vbox = QtGui.QVBoxLayout()
        if col_label:
            self.col_label = QtGui.QLabel(col_label)
            self.col_label.setAlignment(QtCore.Qt.AlignCenter)
            font = self.col_label.font()
            font.setPointSize(20)
            self.col_label.setFont(font)
            self.vbox.addWidget(self.col_label)
    
    def add_row(self, plot_data):
        #plot_data.checkbox = Plot_Checkbox(plot_data)
        plot_data.checkbox.setColor(self.initial_colors.next())
        self.vbox.addWidget(plot_data.checkbox)
        
    def finalize_layout(self):
        self.setLayout(self.vbox)

class Plot_Checkboxes_2D(QtGui.QWidget):
    def __init__(self,checkbox_columns):
        super(Plot_Checkboxes_2D,self).__init__()
        
        hbox = QtGui.QHBoxLayout()
        for checkbox_column in checkbox_columns:
            hbox.addWidget(checkbox_column)
        self.setLayout(hbox)

class XY_Plot_Data(object):
    def __init__(self, parent_plot, label = '', name = ''):
        self.mplot = parent_plot
        self.plot = None
        self.label = label
        self.name = name
        self.checkbox = Plot_Checkbox(self)
        self.is_active = True
        self.active=False
        self.x_window = 5.
        
    def add_plot(self, color='red'):
        self.plot = self.mplot.plot()
        self.plot.setPen(color)
    
    def remove_plot(self):
        self.mplot.removeItem(self.plot)
        self.plot = None
    
    def change_color(self, color):
        if self.plot:
            self.plot.setPen(color)
        
    def change_x_window(self, x):
        #if self.is_active:
        self.x_window = x
            
    def get_xy(self):
        pass
    
class XY_Line_Plots(pg.PlotWidget):
    def __init__(self,parent=None,xlabel=('Time','s')):
        #super(XY_Line_Plots, self).__init__(parent)
        pg.PlotWidget.__init__(self,parent=parent)
        
        self.xydatas = []
        
        self.x_window = 5.0 # seconds
        
        self._active = False
        
        self.setLabel('bottom', xlabel[0], units=xlabel[1])
        self.xlabel = xlabel
        
        self.disableAutoRange()
        self.setMouseEnabled(x=False,y=True)
        
    def update_plots(self):
        if self._active:
            #self.setXRange(-self.x_window,0)
            for xydata in self.xydatas:
                if xydata.plot:
                    x,y = xydata.get_xy()
                    #print min(x),max(x)
                    #xydata.plot.setData(x,y,clipToView=True)                
                    xydata.plot.setData(x,y)
                    
    def change_x_window(self, x):
        #if self.active:
        self.x_window = x
        self.setXRange(-self.x_window,0)
        for xydata in self.xydatas:
            xydata.change_x_window(x)

    #def set_active(self):
    #    if self.active:
    #        self.active = False
    #    else:
    #        self.active = True
    #    for xydata in self.xydatas:
    #        xydata.active = self.active
    #
    
    def set_active(self,which):
        self._active = which
        for xydata in self.xydatas:
            xydata.active = self._active
        
    def add_data(self, xy_plot_data):
        self.xydatas.append(xy_plot_data)
        return self.xydatas[-1]
    
    def save_snapshot(self,filename):
        data_fields = []
        data = []
        for xydata in self.xydatas:
            if xydata.plot:
                data_fields.append('%s %s' %(self.xlabel[0],xydata.name))
                data_fields.append(xydata.name)
                x,y = xydata.get_xy()
                data.append(x)
                data.append(y)
        column_data = izip_longest(*data)
        snapshot_file = open(filename,'wb')
        csv_writer = csv.writer(snapshot_file)
        csv_writer.writerow(data_fields)
        csv_writer.writerows(column_data)
        snapshot_file.close()
        
class X_Window_Control(QtGui.QWidget):
    def __init__(self, default_x_window=1.0):
        super(X_Window_Control, self).__init__()
    
        self.plots = []
            
        self.default_x_window = default_x_window
        self.x_window_slider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.x_window_slider_label = QtGui.QLabel(self)
        self.x_window_slider.setFocusPolicy(QtCore.Qt.NoFocus)
        self.x_window_slider.setRange(1,1000*10)
        self.x_window_slider.setSingleStep(1)
        self.x_window_slider.valueChanged.connect(self.change_x_window)
        self.x_window_slider.setValue(self.default_x_window*1000)
    
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.x_window_slider)
        layout.addWidget(self.x_window_slider_label)
        self.setLayout(layout)
    
        self.change_x_window(default_x_window*1000)
        
    def add_plots(self,plots):
        self.plots.extend(plots)
        self.change_x_window(self.default_x_window*1000)
        
    def change_x_window(self, value):
        x = value/1000.
        self.x_window_slider_label.setText('%.3f s' %x)
        for plot in self.plots:
            plot.change_x_window(x)
