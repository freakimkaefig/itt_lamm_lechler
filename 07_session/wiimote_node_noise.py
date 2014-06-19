#!/usr/bin/env python
# coding: utf-8
# -*- coding: utf-8 -*-

from pyqtgraph.flowchart import Flowchart, Node
from pyqtgraph.flowchart.library.common import CtrlNode
import pyqtgraph.flowchart.library as fclib
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import random

import wiimote

###############################################################################################################
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
        }
        self.wiimote = None
        self._acc_vals = []
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
        self.btaddr = "18:2a:7b:f3:f1:68" # for ease of use
        self.text.setText(self.btaddr)
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_all_sensors)
    
        Node.__init__(self, name, terminals=terminals)
        

    def update_all_sensors(self):
        if self.wiimote == None:
            return
        self._acc_vals = self.wiimote.accelerometer
        # todo: other sensors...
        self.update()

    def update_accel(self, acc_vals):
        self._acc_vals = acc_vals
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
        if len(self.btaddr) == 17 :
            self.connect_button.setText("connecting...")
            self.wiimote = wiimote.connect(self.btaddr)
            if self.wiimote == None:
                self.connect_button.setText("try again")
            else:
                self.connect_button.setText("disconnect")
                self.set_update_rate(self.update_rate_input.value())

    def set_update_rate(self, rate):
        if rate == 0: # use callbacks for max. update rate
            self.wiimote.accelerometer.register_callback(self.update_accel)
            self.update_timer.stop()
        else:
            self.wiimote.accelerometer.unregister_callback(self.update_accel)
            self.update_timer.start(1000.0/rate)

    def process(self, **kwdargs):
        x,y,z = self._acc_vals
        return {'accelX': np.array([x]), 'accelY': np.array([y]), 'accelZ': np.array([z])}
        
fclib.registerNodeType(WiimoteNode, [('Sensor',)])

###############################################################################################################
class BufferNode(CtrlNode):
    """
    Buffers the last n samples provided on input and provides them as a list of
    length n on output.
    A spinbox widget allows for setting the size of the buffer. 
    Default size is 32 samples.
    """
    nodeName = "Buffer"
    uiTemplate = [
        ('size',  'spin', {'value': 100.0, 'step': 1.0, 'range': [0.0, 128.0]}),
    ]

    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),  
            'dataOut': dict(io='out'), 
        }
        self._buffer = np.array([])
        CtrlNode.__init__(self, name, terminals=terminals)
        
    def process(self, **kwds):
        size = int(self.ctrls['size'].value())
        buffersize = size
        self._buffer = np.append(self._buffer, kwds['dataIn'])
        self._buffer = self._buffer[-size:]
        output = self._buffer
        return {'dataOut': output}

fclib.registerNodeType(BufferNode, [('Data',)])

###############################################################################################################
class NoiseNode(CtrlNode):
    """
    Adds Noise to data array
    """
    nodeName = "Noise"
    uiTemplate = [
        ('size',  'spin', {'value': 100.0, 'step': 1.0, 'range': [0.0, 128.0]}),
        ('noise',  'spin', {'value': 15, 'step': 1.0, 'range': [0.0, 128.0]}),
    ]

    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),  
            'dataOut': dict(io='out'), 
        }
        self._values = np.array([])
        CtrlNode.__init__(self, name, terminals=terminals)
        
    def process(self, **kwds):
        size = int(self.ctrls['noise'].value())
        noise = [random.randrange(-(size), size, 1) for _ in range(int(self.ctrls['size'].value()))]
        self._values = kwds['dataIn'] + noise
        output = self._values
        return {'dataOut': output}
    
fclib.registerNodeType(NoiseNode, [('Data',)])

###############################################################################################################
class ConvolutionNode(Node):
    nodeName = 'Convolution'

    def __init__(self, name):
        self.plot = None
        self.curveOrig = None
        self.curveNoise = None
        self.curveKernel = None
        self.curveConv = None
        
        self.kernel = [ 0 for i in range(0,100) ]
        for i in range(45,55):
            self.kernel[i] = 0.1  # range von 45 bis 55 = 10 --> 0.1 (ein zehntel!)
        
        Node.__init__(self, name, terminals={
            'origIn': dict(io='in'),
            'noiseIn': dict(io='in'),
            'convData': dict(io='out'),
        })

    def setPlot(self, plot):
        self.plot = plot
        self.curveOrig = self.plot.plot(pen='y')
        self.curveNoise = self.plot.plot(pen='g')
        self.curveKernel = self.plot.plot(pen='b')
        self.curveConv = self.plot.plot(pen='r')

    def process(self, origIn, noiseIn, display=True):
        self.curveOrig.setData(origIn)
        self.curveNoise.setData(noiseIn)
        
        conv = np.convolve(noiseIn, self.kernel, mode='same')
        print conv
        #self.curveKernel.setData(self.kernel)
        self.curveConv.setData(conv)
        return {'convData': conv}
        
fclib.registerNodeType(ConvolutionNode, [('Display',)])

###############################################################################################################
class SpectrumNode(CtrlNode):
    nodeName = 'Spectrum'
    uiTemplate = [
        ('size',  'spin', {'value': 100.0, 'step': 1.0, 'range': [0.0, 128.0]}),
    ]

    def __init__(self, name):
        self.plot = None
        self.curveOrig = None
        self.curveNoise = None
        
        CtrlNode.__init__(self, name, terminals={
            'origIn': dict(io='in'),
            'noiseIn': dict(io='in'),
            'filterIn': dict(io='in'),
        })

    def setPlot(self, plot):
        self.plot = plot
        self.curveOrig = self.plot.plot(pen='y')
        self.curveNoise = self.plot.plot(pen='g')
        self.curveFilter = self.plot.plot(pen='r')

    def process(self, origIn, noiseIn, filterIn display=True):
        # sensor data
        y = origIn
        Fs = int(self.ctrls['size'].value())
        n = len(y)
        k = np.arange(n)
        T = n/Fs
        frq = k/T
        frq = frq[range(n/2)]
        Y = np.fft.fft(y)/n
        Y = Y[range(n/2)]
        self.curveOrig.setData(frq,abs(Y))

        # sensor data + noise
        y = noiseIn
        Fs = int(self.ctrls['size'].value())
        n = len(y)
        k = np.arange(n)
        T = n/Fs
        frq = k/T
        frq = frq[range(n/2)]
        Y = np.fft.fft(y)/n
        Y = Y[range(n/2)]
        self.curveNoise.setData(frq,abs(Y))

        # filtered sensor + noise data
        y = filterIn
        Fs = int(self.ctrls['size'].value())
        n = len(y)
        k = np.arange(n)
        T = n/Fs
        frq = k/T
        frq = frq[range(n/2)]
        Y = np.fft.fft(y)/n
        Y = Y[range(n/2)]
        self.curveFilter.setData(frq,abs(Y))

fclib.registerNodeType(SpectrumNode, [('Display',)])

###############################################################################################################
if __name__ == '__main__':
    import sys
    app = QtGui.QApplication([])
    win = QtGui.QMainWindow()
    win.setWindowTitle('WiimoteNode demo')
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

    pw1 = pg.PlotWidget()
    pw1.plot(pen='y')
    layout.addWidget(pw1, 1, 1)
    pw1.setYRange(0, 1024)

    pw1Node = fc.createNode('PlotWidget', pos=(300, 150))
    pw1Node.setPlot(pw1)

    pw2 = pg.PlotWidget()
    pw2.plot(pen='g')
    layout.addWidget(pw2, 1, 2)
    pw2.setYRange(0, 1024)

    pw2Node = fc.createNode('PlotWidget', pos=(450, 150))
    pw2Node.setPlot(pw2)

    wiimoteNode = fc.createNode('Wiimote', pos=(0, 0), )
    bufferNode = fc.createNode('Buffer', pos=(150, -150))
    noiseNode = fc.createNode('Noise', pos=(300, -150))    

    fc.connectTerminals(wiimoteNode['accelX'], bufferNode['dataIn'])
    fc.connectTerminals(bufferNode['dataOut'], noiseNode['dataIn'])
    fc.connectTerminals(bufferNode['dataOut'], pw1Node['In'])
    fc.connectTerminals(noiseNode['dataOut'], pw2Node['In'])
    
    pw3 = pg.PlotWidget()
    layout.addWidget(pw3, 0, 1)
    pw3.setYRange(0, 1024)
    convNode = fc.createNode('Convolution', pos=(450, -300))
    convNode.setPlot(pw3)
    fc.connectTerminals(bufferNode['dataOut'], convNode['origIn'])
    fc.connectTerminals(noiseNode['dataOut'], convNode['noiseIn'])
    
    pw4 = pg.PlotWidget()
    layout.addWidget(pw4, 0, 2)
    pw4.setYRange(0, 200)
    specNode = fc.createNode('Spectrum', pos=(600, -300))
    specNode.setPlot(pw4)
    fc.connectTerminals(bufferNode['dataOut'], specNode['origIn'])
    fc.connectTerminals(noiseNode['dataOut'], specNode['noiseIn'])
    fc.connectTerminals(convNode['convData'], specNode['filterIn'])

    win.show()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
