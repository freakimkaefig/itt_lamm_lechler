#!/usr/bin/env python
# coding: utf-8
# -*- coding: utf-8 -*-

from pyqtgraph.flowchart import Flowchart, Node
from pyqtgraph.flowchart.library.common import CtrlNode
import pyqtgraph.flowchart.library as fclib
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import time
import re
import wiimote


class BufferNode(CtrlNode):
    """
    Buffers the last n samples provided on input and provides them as a list of
    length n on output.
    A spinbox widget allows for setting the size of the buffer.
    Default size is 32 samples.
    """
    nodeName = "Buffer"
    uiTemplate = [
        ('size',  'spin', {'value': 32.0, 'step': 1.0, 'range': [0.0, 128.0]}),
    ]

    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),
            'buttons': dict(io='in'),
            'dataOut': dict(io='out'),
        }
        self._buffer = np.array([])
        self.buttons = None
        self.plusPressed = False
        self.minusPressed = False

        CtrlNode.__init__(self, name, terminals=terminals)

    def increase_buffer_size(self):
        size = self.ctrls['size'].value()
        self.ctrls['size'].setValue(size + 1.0)

    def decrease_buffer_size(self):
        size = self.ctrls['size'].value()
        self.ctrls['size'].setValue(size - 1.0)

    def process(self, **kwds):
        size = int(self.ctrls['size'].value())
        self._buffer = np.append(self._buffer, kwds['dataIn'])
        self._buffer = self._buffer[-size:]
        self.buttons = kwds['buttons']

        # check buttons to increase or decrease buffer size
        if self.buttons['Plus'] is True:
            self.plusPressed = True
        if self.buttons['Plus'] is False:
            if self.plusPressed:
                self.plusPressed = False
                self.increase_buffer_size()
        if self.buttons['Minus'] is True:
            self.minusPressed = True
        if self.buttons['Minus'] is False:
            if self.minusPressed:
                self.minusPressed = False
                self.decrease_buffer_size()

        output = self._buffer
        return {'dataOut': output}

fclib.registerNodeType(BufferNode, [('Data',)])


class WiimoteNode(Node):
    """
    Outputs sensor data from a Wiimote.

    Supported sensors: accelerometer (3 axis)
    Text input box allows for setting a Bluetooth MAC address.
    Pressing the "connect" button tries connecting to the Wiimote.
    Update rate can be changed via a spinbox widget. Setting it to "0"
    activates callbacks everytime a new sensor value arrives (which is
    quite often -> performance hit)
    """
    nodeName = "Wiimote"

    def __init__(self, name):
        terminals = {
            'accelX': dict(io='out'),
            'accelY': dict(io='out'),
            'accelZ': dict(io='out'),
            'ir': dict(io='out'),
            'buttons': dict(io='out'),
        }
        self.wiimote = None
        self._acc_vals = []
        self._ir_vals = []
        self._buttons = []
        self.bufferNode = None
        self.plotNode = None
        self.ui = QtGui.QWidget()
        self.layout = QtGui.QGridLayout()

        label = QtGui.QLabel("Bluetooth MAC address:")
        self.layout.addWidget(label)
        self.text = QtGui.QLineEdit()
        self.layout.addWidget(self.text)
        label2 = QtGui.QLabel("Update rate (Hz)")
        self.layout.addWidget(label2)
        self.update_rate_input = QtGui.QSpinBox()
        self.update_rate_input.setMinimum(0)
        self.update_rate_input.setMaximum(60)
        self.update_rate_input.setValue(20)
        self.update_rate_input.valueChanged.connect(self.set_update_rate)
        self.layout.addWidget(self.update_rate_input)

        self.connect_button = QtGui.QPushButton("connect")
        self.layout.addWidget(self.connect_button)
        self.ui.setLayout(self.layout)
        self.connect_button.clicked.connect(self.connect_wiimote)
        # pass wiimotes bluetooth mac adress as param...
        if len(sys.argv) == 2:
            # print("args.: ", sys.argv[1])
            self.btaddr = sys.argv[1]
        else:
            # ...or hard-code it here
            self.btaddr = "B8:AE:6E:1B:A3:9B"
        self.text.setText(self.btaddr)
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_all_sensors)

        Node.__init__(self, name, terminals=terminals)

    def update_all_sensors(self):
        if self.wiimote is None:
            return
        # Accelerometer
        self._acc_vals = self.wiimote.accelerometer
        # IRCamera sensor
        self._ir_vals = self.wiimote.ir
        # Buttons
        self._buttons = self.wiimote.buttons
        # self.wiimote.buttons.register_callback(self.buttons)
        # todo: other sensors...

        self.update()

    def update_accel(self, acc_vals):
        self._acc_vals = acc_vals
        self.update()

    def update_ir(self, ir_vals):
        self._ir_vals = ir_vals
        self.update()

    def ctrlWidget(self):
        return self.ui

    def connect_wiimote(self):
        self.btaddr = str(self.text.text()).strip()
        if self.wiimote is not None:
            self.wiimote.disconnect()
            self.wiimote = None
            self.connect_button.setText("connect")
            return
        if len(self.btaddr) == 17:
            self.connect_button.setText("connecting...")
            self.wiimote = wiimote.connect(self.btaddr)
            if self.wiimote is None:
                self.connect_button.setText("try again")
            else:
                self.connect_button.setText("disconnect")
                self.set_update_rate(self.update_rate_input.value())

    def set_update_rate(self, rate):
        if rate == 0:  # use callbacks for max. update rate
            self.wiimote.accelerometer.register_callback(self.update_accel)
            self.wiimote.ir.register_callback(self.update_ir)
            self.update_timer.stop()
        else:
            self.wiimote.accelerometer.unregister_callback(self.update_accel)
            self.wiimote.ir.unregister_callback(self.update_ir)
            self.update_timer.start(1000.0/rate)

    def process(self, **kwdargs):
        x, y, z = self._acc_vals
        ir = self._ir_vals
        return {'accelX': np.array([x]), 'accelY': np.array([y]),
                'accelZ': np.array([z]), 'ir': np.array([ir]),
                'buttons': self._buttons}

fclib.registerNodeType(WiimoteNode, [('Sensor',)])


class IrLightNode(Node):
    """
    Calculates the most intense light source of ir camera values given.
    Returns the average x-, and y-position of the 'pointer' (most
    intense light source)
    """

    nodeName = "IrLightNode"

    def __init__(self, name):
        terminals = {
            'In': dict(io='in'),
            'Out': dict(io='out'),
        }
        self._ir_vals = []
        self._xy_vals = []
        self.avg_val = None

        Node.__init__(self, name, terminals=terminals)

    def calculate_max_light(self, ir):
        if ir.any():
            self._xy_vals = []
            maxLight = max(ir, key=lambda x: x['size'])
            for val in ir:
                if int(maxLight['id']) == int(val['id']):
                    self._xy_vals.append((val['x'], val['y']))

            x = self._xy_vals
            self.avg_val = tuple(map(lambda y: sum(y) / float(len(y)),
                                     zip(*x)))

    def process(self, **kwds):
        self.calculate_max_light(kwds['In'])
        return {'Out': self.avg_val}

fclib.registerNodeType(IrLightNode, [('Data',)])


class GesturePlotNode(Node):
    """
    Plots the current position of the 'pointer' (IR light source)
    Also plots the path of gesture during recording (visual feedback)
    """
    nodeName = "GesturePlotNode"

    def __init__(self, name):
        terminals = {
            'positionIn': dict(io='in'),
            'pathIn': dict(io='in'),
        }
        self._ir_vals = []
        self._xy_vals = []
        self.plot = None
        self.spiPos = None
        self.spiPath = None
        self.avg_val = (0, 0)

        Node.__init__(self, name, terminals=terminals)

    def plotPosition(self, val):
        # plotting current position of the "pointer" (ir light source)
        if val is not None:
            self.spiPos.clear()
            points = [{'pos': [1024 - val[0], 768 - val[1]], 'data': 1}]
            self.spiPos.addPoints(points)
            self.plot.addItem(self.spiPos)

    def plotPath(self, vals):
        # plotting path while recording (visual feedback)
        if vals is not None:
            points = []
            counter = 1
            for point in vals:
                points.append({'pos': [1024 - point[0], 768 - point[1]], 'data': counter})
                counter += 1
            self.spiPath.addPoints(points)
            self.plot.addItem(self.spiPath)

    def setPlot(self, plot):
        self.plot = plot
        self.spiPos = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 255))
        self.spiPath = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 0, 0, 255), ls='solid', marker='o')

        self.plot.setXRange(0, 1024)
        self.plot.setYRange(0, 768)

    def process(self, **kwds):
        self.plotPosition(kwds['positionIn'])
        self.plotPath(kwds['pathIn'])

fclib.registerNodeType(GesturePlotNode, [('Display',)])


class GestureNode(Node):
    """
    Handles gesture recognition of point data from
    wiimote ir camera
    """

    nodeName = "GestureNode"

    def __init__(self, name):
        terminals = {
            'In': dict(io='in'),
            'buttons': dict(io='in'),
            'Out': dict(io='out'),
        }
        self.path = []
        self.buttons = None
        self.aPressed = False
        self.recognizedGesture = None

        Node.__init__(self, name, terminals=terminals)

    def setLabel(self, label):
        self.label = label
        self.label.setStyleSheet("font: 24pt; color:#33a;")

    def distance(self, x, y):
        dx = x[0] - y[0]
        dy = x[1] - y[1]
        return sqrt(dx*dx - dy*dy)

    def total_length(self, point_list):
        p1 = point_list[0]
        length = 0.0
        for i in range(1, len(point_list)):
            length += distance(p1, point_list[i])
            p1 = point_list[i]
        return length

    def resample(self, point_list, step_count=64):
        # 1$ recognizer implementation
        newpoints = []
        length = total_length(point_list)
        stepsize = length/step_count
        curpos = 0
        newpoints.appen(point_list[0])
        i = 1
        while i < len(point_list):
            p1 = point_list[i-1]
            d = distance(p1, point_list[i])
            if curpos + d >= stepsize:
                nx = p1[0] + ((stepsize - curpos) / d) * (point_list[i][0] - p1[0])
                ny = p1[1] + ((stepsize - curpos) / d) * (point_list[i][1] - p1[1])
                newpoints.append([nx, ny])
                point_list.insert(i, [nx, ny])
                curpos = 0
            else:
                curpos += d
            i += 1
        return newpoints

    def saveTemplate(self, path):
        print "saveTemplate"
        # save path as template

    def checkRecognizedGesture(self, path):
        # check for gestures
        if recognizedGesture is not None:
            self.label.setText(recognizedGesture)
        else:
            self.label.setText("no gesture recognized")

    def recordGesture(self, value):
        self.path.append(value)

    def process(self, **kwds):
        self.buttons = kwds['buttons']
        if self.buttons['A'] is True:
            self.aPressed = True
            self.recordGesture(kwds['In'])
        if self.buttons['A'] is False:
            if self.aPressed:
                self.resample(self.path)
                self.path = []
                self.aPressed = False

        """
        detect at least three different predefined shapes (e.g. circle, square, ...)
        gesture data is recorded while pressing the 'A' button and analyzed on release
        possible to learn new shapes/create new templates by using the 'B' button while recording
        display raw data and templates as graph + a text label indicating the recognized gesture
        """

        return {'Out': self.path}

fclib.registerNodeType(GestureNode, [('Display',)])


if __name__ == '__main__':
    import sys
    app = QtGui.QApplication([])
    win = QtGui.QMainWindow()
    win.setWindowTitle('Gestures')
    cw = QtGui.QWidget()
    win.setCentralWidget(cw)
    layout = QtGui.QGridLayout()
    cw.setLayout(layout)

    # Create an empty flowchart with a single input and output
    fc = Flowchart(terminals={
        'dataIn': {'io': 'in'},
        'dataOut': {'io': 'out'}
    })
    w = fc.widget()

    layout.addWidget(fc.widget(), 0, 0, 2, 1)

    view = pg.GraphicsLayoutWidget()
    layout.addWidget(view, 0, 1, 2, 1)

    wiimoteNode = fc.createNode('Wiimote', pos=(0, 0), )
    bufferNodeIr = fc.createNode('Buffer', pos=(150, 150))
    irLightNode = fc.createNode('IrLightNode', pos=(300, 150))
    gestureNode = fc.createNode('GestureNode', pos=(300, 300))
    gesturePlotNode = fc.createNode('GesturePlotNode', pos=(450, 150))

    # connect ir camera
    plotter = view.addPlot()
    gesturePlotNode.setPlot(plotter)

    # creating label for recognized gesture
    gestureLabel = QtGui.QLabel("please connect WiiMote")
    layout.addWidget(gestureLabel, 2, 0)
    gestureNode.setLabel(gestureLabel)

    fc.connectTerminals(wiimoteNode['ir'], bufferNodeIr['dataIn'])
    fc.connectTerminals(wiimoteNode['buttons'], bufferNodeIr['buttons'])
    fc.connectTerminals(wiimoteNode['buttons'], gestureNode['buttons'])
    fc.connectTerminals(bufferNodeIr['dataOut'], irLightNode['In'])
    fc.connectTerminals(irLightNode['Out'], gesturePlotNode['positionIn'])
    fc.connectTerminals(irLightNode['Out'], gestureNode['In'])
    fc.connectTerminals(gestureNode['Out'], gesturePlotNode['pathIn'])

    win.show()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
