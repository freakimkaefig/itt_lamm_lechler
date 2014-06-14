#!/usr/bin/env python
# coding: utf-8
# -*- coding: utf-8 -*-

from pyqtgraph.flowchart import Flowchart, Node
from pyqtgraph.flowchart.library.common import CtrlNode
import pyqtgraph.flowchart.library as fclib
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np

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
            'dataOut': dict(io='out'),
        }
        self._buffer = np.array([])
        CtrlNode.__init__(self, name, terminals=terminals)

    def increase_buffer_size(self):
        size = self.ctrls['size'].value()
        self.ctrls['size'].setValue(size + 1.0)

    def decrease_buffer_size(self):
        if self.ctrls['size'].value() > 0:
            size = self.ctrls['size'].value()
            self.ctrls['size'].setValue(size - 1.0)

    def process(self, **kwds):
        size = int(self.ctrls['size'].value())
        #print kwds['dataIn']
        self._buffer = np.append(self._buffer, kwds['dataIn'])
        self._buffer = self._buffer[-size:]
        # output = map(int, self._buffer)
        #print self._buffer
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
        }
        self.wiimote = None
        self._acc_vals = []
        self._ir_vals = []
        self._buttons = []
        self.bufferNode = None
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
        #self.wiimote.buttons.register_callback(self.buttons)
        # todo: other sensors...

        self.update()

    def set_buffer_node(self, bufferNode):
        self.bufferNode = bufferNode

    def update_accel(self, acc_vals):
        self._acc_vals = acc_vals
        self.update()
  
    def update_buttons(self, buttons):
        if buttons:
            if buttons[0] == ('Minus', True):
                self.bufferNode.decrease_buffer_size()
            if buttons[0] == ('Plus', True):
                self.bufferNode.increase_buffer_size()

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
        self.wiimote.buttons.register_callback(self.update_buttons)

    def process(self, **kwdargs):
        x, y, z = self._acc_vals
        ir = self._ir_vals
        return {'accelX': np.array([x]), 'accelY': np.array([y]),
                'accelZ': np.array([z]), 'ir': np.array([ir])}


class IrPlotNode(Node):
    """
    Plots ir sensor data data from a Wiimote
    """
    nodeName = "IrPlotNode"

    def __init__(self, name):
        terminals = {
            'irData': dict(io='in'),
            'xOut': dict(io='out'),
            'yOut': dict(io='out'),
        }
        self._ir_vals = []
        self._xy_vals = []
        self.plot = None
        self.spi = None
        self.avg_val = (0, 0)

        Node.__init__(self, name, terminals=terminals)

    def calculate_max_light(self, ir):
        self._xy_vals = []
        maxLight = max(ir, key=lambda x: x['size'])
        for val in ir:
            if int(maxLight['id']) == int(val['id']):
                self._xy_vals.append((val['x'], val['y']))
                #print "XY", self._xy_vals
                x = self._xy_vals
                self.avg_val = tuple(map(lambda y: sum(y) / float(len(y)),
                                         zip(*x)))
                self.plotVal(self.avg_val)

    def plotVal(self, val):
        #print val
        self.spi.clear()
        points = [{'pos': [val[0], val[1]], 'data': 1}]
        self.spi.addPoints(points)
        self.plot.addItem(self.spi)

    def setPlot(self, plot):
        self.plot = plot
        self.spi = pg.ScatterPlotItem(size=10,
                                      pen=pg.mkPen(None),
                                      brush=pg.mkBrush(255, 255, 255, 255))

        self.plot.setXRange(0, 1500)
        self.plot.setYRange(0, 1500)

    def process(self, irData):
        self._ir_vals = irData
        self.calculate_max_light(self._ir_vals)
        return {'xOut': 1, 'yOut': 2}


fclib.registerNodeType(WiimoteNode, [('Sensor',)])
fclib.registerNodeType(IrPlotNode, [('Display',)])

if __name__ == '__main__':
    import sys
    app = QtGui.QApplication([])
    win = QtGui.QMainWindow()
    win.setWindowTitle('Wiipoint 2D')
    cw = QtGui.QWidget()
    win.setCentralWidget(cw)
    layout = QtGui.QGridLayout()
    cw.setLayout(layout)

    ## Create an empty flowchart with a single input and output
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
    irPlotNode = fc.createNode('IrPlotNode', pos=(300, 150))

    # connect 'Plus' and 'Minus' buttons
    wiimoteNode.set_buffer_node(bufferNodeIr)

    # connect ir camera
    plotter = view.addPlot()
    irPlotNode.setPlot(plotter)

    fc.connectTerminals(wiimoteNode['ir'], bufferNodeIr['dataIn'])
    fc.connectTerminals(bufferNodeIr['dataOut'], irPlotNode['irData'])

    win.show()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
