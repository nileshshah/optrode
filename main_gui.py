#!/usr/bin/env python
import os, sys, time
import numpy as np

from PySide import QtGui, QtCore
import pyqtgraph as pg

from optrode_gui import Optrode_Monitor
from PM320E_gui import PM_Monitor

from multi_XY_plots import X_Window_Control

class MainWindow(QtGui.QWidget):
    def __init__(self):
        #super(MainWindow,self).__init__()
        QtGui.QWidget.__init__(self)
        self.optrode_window = Optrode_Monitor(parent=self)
        self.pm_window = PM_Monitor(parent=self)
        self.time_control = X_Window_Control()
        self.time_control.add_plots(self.optrode_window.raw_data_monitor.plots)
        self.time_control.add_plots(self.pm_window.raw_data_monitor.plots)
    
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.optrode_window)
        layout.addWidget(self.pm_window)
        layout.addWidget(self.time_control)
        self.setLayout(layout)
        
    def shutdown(self):
        self.optrode_window.shutdown()
        self.pm_window.shutdown()
        
if __name__ == '__main__':
    import cProfile
    app = QtGui.QApplication(sys.argv)
    widget = MainWindow()
    app.aboutToQuit.connect(widget.shutdown)
    widget.resize(1024,768)
    widget.show()
    sys.exit(app.exec_())
