#!/usr/bin/env python
import os,sys

import numpy as np

from PySide import QtGui, QtCore
import pyqtgraph as pg

def color_iter(n_items):
    return iter([pg.colorStr(pg.intColor(i,values=n_items)) \
                               for i in range(n_items)])

class QColorButton(QtGui.QPushButton):
    '''
    Custom Qt Widget to show a chosen color.
    Left-clicking the button shows the color-chooser, while
    right-clicking resets the color to None (no-color).    
    '''

    colorChanged = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(QColorButton, self).__init__(*args, **kwargs)

        self._color = None
        
        self.setMaximumWidth(32)
        self.pressed.connect(self.onColorPicker)
        
    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit()

        # handles different color formats
        try:
            r,g,b,a = pg.colorTuple(self._color)
        except:
            r,g,b,a = pg.colorTuple(pg.mkColor(self._color))
            
        if self._color:
                self.setStyleSheet('background-color: rgba(%d,%d,%d,%d);' %(r,g,b,a))
                self._color = pg.mkColor(self._color)
        else:
            self.setStyleSheet("")
        
    def color(self):
        return self._color

    def onColorPicker(self):
        '''
        Show color-picker dialog to select color.
        Qt will use the native dialog by default.

        '''
        self.setStyleSheet("")
        dlg = QtGui.QColorDialog(self)
        if self._color:
            dlg.setCurrentColor(QtGui.QColor(self._color))

        if dlg.exec_():
            self.setColor(dlg.currentColor().name())
            
    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.RightButton:
            self.setColor(None)

        return super(QColorButton, self).mousePressEvent(e)

