#!/usr/bin/env python
# coding: utf-8
# -*- coding: utf-8 -*-

"""
describe operation of activity recognition system HERE
"""

from pyqtgraph.flowchart import Flowchart, Node
from pyqtgraph.flowchart.library.common import CtrlNode
import pyqtgraph.flowchart.library as fclib
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import random
import wiimote


## initial values
bufferSize = 100
convolutionSize = 6


###############################################################################
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
        self.btaddr = "B8:AE:6E:1B:A3:9B"  # for ease of use
        self.text.setText(self.btaddr)
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_all_sensors)

        Node.__init__(self, name, terminals=terminals)

    def update_all_sensors(self):
        if self.wiimote is None:
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
            self.update_timer.stop()
        else:
            self.wiimote.accelerometer.unregister_callback(self.update_accel)
            self.update_timer.start(1000.0/rate)

    def process(self, **kwdargs):
        x, y, z = self._acc_vals
        return {'accelX': np.array([x]),
                'accelY': np.array([y]),
                'accelZ': np.array([z])}

fclib.registerNodeType(WiimoteNode, [('Sensor',)])


###############################################################################
class BufferNode(CtrlNode):
    """
    Buffers the last n samples provided on input and provides them as a list of
    length n on output.
    A spinbox widget allows for setting the size of the buffer.
    Default size is 32 samples.
    """
    nodeName = "Buffer"
    uiTemplate = [
        ('size',  'spin', {'value': bufferSize, 'step': 2, 'range': [0, 128]}),
    ]

    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),
            'dataOut': dict(io='out'),
        }
        self._buffer = np.array([])

        CtrlNode.__init__(self, name, terminals=terminals)

    def bufferChange(self, event):
        print "Hello"

    def process(self, **kwds):
        #self.ctrls['size'].valueChanged.connect(self.bufferChange)
        size = int(self.ctrls['size'].value())
        buffersize = size
        self._buffer = np.append(self._buffer, kwds['dataIn'])
        self._buffer = self._buffer[-size:]
        output = self._buffer
        return {'dataOut': output}

fclib.registerNodeType(BufferNode, [('Data',)])


###############################################################################
class ConvolutionNode(CtrlNode):
    nodeName = "Convolution"
    uiTemplate = [
        ('size',  'spin', {'value': convolutionSize, 'step': 2, 'range': [0, 20]}),
    ]

    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),
            'convolution': dict(io='out'),
        }

        self.bufferSize = bufferSize
        self.size = convolutionSize
        self.kernel = None

        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, **kwds):
        self.bufferSize = len(kwds['dataIn'])

        self.size = int(self.ctrls['size'].value())
        self.kernel = [0 for i in range(0, self.bufferSize)]
        start = (self.bufferSize / 2) - (self.size / 2)
        end = (self.bufferSize / 2) + (self.size / 2)
        for i in range(start, end):
            # range von 45 bis 55 = 10 --> 0.1 (ein zehntel!)
            self.kernel[i] = float(1.0 / self.size)

        conv = np.convolve(kwds['dataIn'], self.kernel, mode='same')
        return {'convolution': conv}

fclib.registerNodeType(ConvolutionNode, [('Display',)])


###############################################################################
class FftNode(Node):
    nodeName = "Fft"

    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),
            'dataOut': dict(io='out'),
        }

        self.bufferSize = bufferSize

        Node.__init__(self, name, terminals=terminals)

    def process(self, **kwds):
        self.bufferSize = len(kwds['dataIn'])
        data = kwds['dataIn']
        Fs = int(self.bufferSize)
        n = len(data)
        k = np.arange(n)
        T = n/Fs
        frq = k/T
        frq = frq[range(n/2)]
        Y = np.fft.fft(data)/n
        Y = Y[range(n/2)]
        return {'dataOut': abs(Y)}
        #self.curveRaw.setData(frq, abs(Y))

fclib.registerNodeType(FftNode, [('Data',)])


###############################################################################
class PlotNode(Node):
    nodeName = 'PlotNode'

    def __init__(self, name):
        terminals = {
            'rawIn': dict(io='in'),
            'filterIn': dict(io='in'),
        }
        self.once = 0  # control var (deletable)
        self.bufferSize = 10  # fft buffer size
        self.plotWidget = None
        self.curveRaw = None
        self.curveFilter = None
        self.xFftBuffer = np.array([])
        self.lastMeanYFft = []
        self.yFftBuffer = np.array([])
        self.zFftBuffer = np.array([])
        self.currentName = name
        Node.__init__(self, name, terminals)

    def setPlot(self, plotWidget):
        self.plotWidget = plotWidget
        self.curveRaw = self.plotWidget.plot(pen='y')
        self.curveFilter = self.plotWidget.plot(pen='r')

        self.legend = pg.LegendItem(offset=(-1, 1))
        self.legend.addItem(self.curveRaw, 'raw data')
        self.legend.addItem(self.curveFilter, 'convolution filter')
        self.legend.setParentItem(self.plotWidget.getPlotItem())

    def process(self, **kwds):
        self.curveRaw.setData(kwds['rawIn'])
        self.curveFilter.setData(kwds['filterIn'])

fclib.registerNodeType(PlotNode, [('Display',)])


###############################################################################
class ActivityNode(Node):
    nodeName = 'Activity'

    def __init__(self, name):
        terminals = {
            'xRawIn': dict(io='in'),
            'xFilterIn': dict(io='in'),
            'yRawIn': dict(io='in'),
            'yFilterIn': dict(io='in'),
            'zRawIn': dict(io='in'),
            'zFilterIn': dict(io='in'),
        }
        self.once = 0  # control var (deletable)
        self.bufferSize = 100  # fft buffer size
        self.xFftBuffer = np.array([])
        self.yFftBuffer = np.array([])
        self.zFftBuffer = np.array([])
        self.lastMeanXFft = []
        self.lastMeanYFft = []
        self.lastMeanZFft = []
        self.currentName = name
        Node.__init__(self, name, terminals)

    def process(self, **kwds):
        self.xFftBuffer = np.append(self.xFftBuffer, kwds['xFilterIn'])
        self.xFftBuffer = self.xFftBuffer[-self.bufferSize:]
        self.yFftBuffer = np.append(self.yFftBuffer, kwds['yFilterIn'])
        self.yFftBuffer = self.yFftBuffer[-self.bufferSize:]
        self.zFftBuffer = np.append(self.zFftBuffer, kwds['zFilterIn'])
        self.zFftBuffer = self.zFftBuffer[-self.bufferSize:]

        self.lastMeanYFft.append(np.mean(self.yFftBuffer))
        self.lastMeanYFft = self.lastMeanYFft[-self.bufferSize:]
        self.lastMeanXFft.append(np.mean(self.xFftBuffer))
        self.lastMeanXFft = self.lastMeanXFft[-self.bufferSize:]
        self.lastMeanZFft.append(np.mean(self.zFftBuffer))
        self.lastMeanZFft = self.lastMeanZFft[-self.bufferSize:]
        
        """        
        sitzn y~13,1          #x~12,7          #z~10,0
            0 - 14,0       #12,0 - 13,5      #9,0 - 11
            
        stehn y~15,0         #x~12,7          z~12,9
            14,0 - 15,5    #12,4 - 13,0     12,6 - 13,5
            
        gehen y~15,1         #x~12,9            z~12,2
            14,0 - 15,5     #12,6 - 13,2    11,0 - 12,6
            
        rennen y~15,8        x~13,4          #z~12,4
            15,5 - 17     13,1 - 13,7     #12,1 - 12,7
        
        according to: """
        #print "meanFftValues: ", np.mean(self.lastMeanYFft), ", x: ",np.mean(self.lastMeanXFft), ", z: ",np.mean(self.lastMeanZFft)
        
        # results in:
        # sitting:
        if(0.0 <= np.mean(self.lastMeanYFft) and np.mean(self.lastMeanYFft) <= 14.0):
            #if(12.4 <= np.mean(self.lastMeanXFft) <= 13.0):
                #if(9.7 <= np.mean(self.lastMeanZFft) <= 10.3):
                    print "sitting: ", np.mean(self.lastMeanYFft), ", x: ",np.mean(self.lastMeanXFft), ", z: ",np.mean(self.lastMeanZFft)
        # standing:
        if(14.0 <= np.mean(self.lastMeanYFft) and np.mean(self.lastMeanYFft) <= 15.5 and 12.6 <= np.mean(self.lastMeanZFft) and np.mean(self.lastMeanZFft) <= 13.5):
            #if(12.4 <= np.mean(self.lastMeanXFft) <= 13.3):
                #if(12.6 <= np.mean(self.lastMeanZFft) <= 13.5):
                    print "standing: ", np.mean(self.lastMeanYFft), ", x: ",np.mean(self.lastMeanXFft), ", z: ",np.mean(self.lastMeanZFft)
        # walking:
        if(14.0 <= np.mean(self.lastMeanYFft) and np.mean(self.lastMeanYFft) <= 15.5 and 11.0 <= np.mean(self.lastMeanZFft) and np.mean(self.lastMeanZFft) <= 12.6):
            #if(13.4 <= np.mean(self.lastMeanXFft) <= 13.8):
                #if(11.0 <= np.mean(self.lastMeanZFft) <= 12.6):
                    print "walking: ", np.mean(self.lastMeanYFft), ", x: ",np.mean(self.lastMeanXFft), ", z: ",np.mean(self.lastMeanZFft)
        # running:
        if(15.5 <= np.mean(self.lastMeanYFft) and np.mean(self.lastMeanYFft) <= 17.0):
            #if(13.2 <= np.mean(self.lastMeanXFft) <= 14.5):
                #if(12.6 <= np.mean(self.lastMeanZFft) <= 13.0):
                    print "running: ", np.mean(self.lastMeanYFft), ", x: ",np.mean(self.lastMeanXFft), ", z: ",np.mean(self.lastMeanZFft)

fclib.registerNodeType(ActivityNode, [('Display',)])


###############################################################################
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

    # wiimote node
    wiimoteNode = fc.createNode('Wiimote', pos=(0, -300), )

    ### X ###
    # buffer for X
    xBufferNode = fc.createNode('Buffer', pos=(150, -450))
    # convolution filter for X
    xConvNode = fc.createNode('Convolution', pos=(300, -450))
    # plotting raw and filter data of X
    xPlotWidget1 = pg.PlotWidget()
    layout.addWidget(xPlotWidget1, 0, 1)
    xPlotWidget1.setYRange(0, 1024)
    xPlotNode1 = fc.createNode('PlotNode', pos=(450, -450))
    xPlotNode1.setPlot(xPlotWidget1)
    # fft for X
    xRawFftNode = fc.createNode('Fft', pos=(600, -450))
    xConvFftNode = fc.createNode('Fft', pos=(750, -450))
    # plotting fft data of X
    xPlotWidget2 = pg.PlotWidget()
    layout.addWidget(xPlotWidget2, 0, 2)
    xPlotWidget2.setYRange(0, 150)
    xPlotNode2 = fc.createNode('PlotNode', pos=(900, -450))
    xPlotNode2.setPlot(xPlotWidget2)
    # connecting nodes
    fc.connectTerminals(wiimoteNode['accelX'], xBufferNode['dataIn'])
    fc.connectTerminals(xBufferNode['dataOut'], xConvNode['dataIn'])
    fc.connectTerminals(xBufferNode['dataOut'], xPlotNode1['rawIn'])
    fc.connectTerminals(xConvNode['convolution'], xPlotNode1['filterIn'])
    fc.connectTerminals(xBufferNode['dataOut'], xRawFftNode['dataIn'])
    fc.connectTerminals(xConvNode['convolution'], xConvFftNode['dataIn'])
    fc.connectTerminals(xRawFftNode['dataOut'], xPlotNode2['rawIn'])
    fc.connectTerminals(xConvFftNode['dataOut'], xPlotNode2['filterIn'])

    ### Y ###
    # buffer for Y
    yBufferNode = fc.createNode('Buffer', pos=(150, -300))
    # convolution filter for Y
    yConvNode = fc.createNode('Convolution', pos=(300, -300))
    # plotting raw and filter data of Y
    yPlotWidget1 = pg.PlotWidget()
    layout.addWidget(yPlotWidget1, 1, 1)
    yPlotWidget1.setYRange(0, 1024)
    yPlotNode1 = fc.createNode('PlotNode', pos=(450, -300))
    yPlotNode1.setPlot(yPlotWidget1)
    # fft for Y
    yRawFftNode = fc.createNode('Fft', pos=(600, -300))
    yConvFftNode = fc.createNode('Fft', pos=(750, -300))
    # plotting fft data of Y
    yPlotWidget2 = pg.PlotWidget()
    layout.addWidget(yPlotWidget2, 1, 2)
    yPlotWidget2.setYRange(0, 150)
    yPlotNode2 = fc.createNode('PlotNode', pos=(900, -300))
    yPlotNode2.setPlot(yPlotWidget2)
    # connecting nodes
    fc.connectTerminals(wiimoteNode['accelY'], yBufferNode['dataIn'])
    fc.connectTerminals(yBufferNode['dataOut'], yConvNode['dataIn'])
    fc.connectTerminals(yBufferNode['dataOut'], yPlotNode1['rawIn'])
    fc.connectTerminals(yConvNode['convolution'], yPlotNode1['filterIn'])
    fc.connectTerminals(yBufferNode['dataOut'], yRawFftNode['dataIn'])
    fc.connectTerminals(yConvNode['convolution'], yConvFftNode['dataIn'])
    fc.connectTerminals(yRawFftNode['dataOut'], yPlotNode2['rawIn'])
    fc.connectTerminals(yConvFftNode['dataOut'], yPlotNode2['filterIn'])

    ### Z ###
    # buffer for Z
    zBufferNode = fc.createNode('Buffer', pos=(150, -150))
    # convolution filter for Z
    zConvNode = fc.createNode('Convolution', pos=(300, -150))
    # plotting raw and filter data of Z
    zPlotWidget1 = pg.PlotWidget()
    layout.addWidget(zPlotWidget1, 2, 1)
    zPlotWidget1.setYRange(0, 1024)
    zPlotNode1 = fc.createNode('PlotNode', pos=(450, -150))
    zPlotNode1.setPlot(zPlotWidget1)
    # fft for Z
    zRawFftNode = fc.createNode('Fft', pos=(600, -150))
    zConvFftNode = fc.createNode('Fft', pos=(750, -150))
    # plotting fft data of Z
    zPlotWidget2 = pg.PlotWidget()
    layout.addWidget(zPlotWidget2, 2, 2)
    zPlotWidget2.setYRange(0, 150)
    zPlotNode2 = fc.createNode('PlotNode', pos=(900, -150))
    zPlotNode2.setPlot(zPlotWidget2)
    # connecting nodes
    fc.connectTerminals(wiimoteNode['accelZ'], zBufferNode['dataIn'])
    fc.connectTerminals(zBufferNode['dataOut'], zConvNode['dataIn'])
    fc.connectTerminals(zBufferNode['dataOut'], zPlotNode1['rawIn'])
    fc.connectTerminals(zConvNode['convolution'], zPlotNode1['filterIn'])
    fc.connectTerminals(zBufferNode['dataOut'], zRawFftNode['dataIn'])
    fc.connectTerminals(zConvNode['convolution'], zConvFftNode['dataIn'])
    fc.connectTerminals(zRawFftNode['dataOut'], zPlotNode2['rawIn'])
    fc.connectTerminals(zConvFftNode['dataOut'], zPlotNode2['filterIn'])

    ### ACTIVITY ###
    # creating activity tracker
    activity = fc.createNode('Activity', pos=(750, 0))
    # connecting nodes
    fc.connectTerminals(xRawFftNode['dataOut'], activity['xRawIn'])
    fc.connectTerminals(yRawFftNode['dataOut'], activity['yRawIn'])
    fc.connectTerminals(zRawFftNode['dataOut'], activity['zRawIn'])
    fc.connectTerminals(xConvFftNode['dataOut'], activity['xFilterIn'])
    fc.connectTerminals(yConvFftNode['dataOut'], activity['yFilterIn'])
    fc.connectTerminals(zConvFftNode['dataOut'], activity['zFilterIn'])

    win.show()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()



