#!/usr/bin/env python
# coding: utf-8
# -*- coding: utf-8 -*-

"""
The sensor data of all three axes is stored in seperate buffers with a
default length of 100. To demonstrate the difference, the raw values are
plotted besides these values combined with a square convolution filter to
reduce noise. The filtered values are used for a fast fourier transform to
detect frequencies of movements.
The last node “Activity” receives the filtered data (convolution + fft) from
each axes. After collecting a reasonable amount of data from each axis,
the recognition of the activites ‘sitting’, ‘standing’, ‘walking’ and
‘running’ is mostly determined by the changes within the values of the
Y-axis.
By calculating the mean of the last 100 values of each axes the activity
recognition is more stable and less fragile towards variations within
those values. Once a activity is recognised it is temporarily saved.
By counting the occurence of the last 100 recognised activities we ultimately
determine the displayed activity.
By doing so we lowered our sights regarding the speed of activity recognition
but we are able to tell the currentliy performed activity fairly accurate.
However the reviewed values are heavily depending on the rotation of the
wiimote inside ones trouser pocket. The most accurate results were received
when the  front of the wiimote (IR sensor) was pointing towards the ground
while the buttons (e.g. ‘+’ or ‘A’) where facing ones leg.
"""

from pyqtgraph.flowchart import Flowchart, Node
from pyqtgraph.flowchart.library.common import CtrlNode
import pyqtgraph.flowchart.library as fclib
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import random
import wiimote


# initial values
bufferSize = 100
convolutionSize = 6


###############################################################################
class WiimoteNode(Node):
    """
    Outputs sensor data from a Wiimote.

    Supported sensors: accelerometer (3 axes)
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
        if len(sys.argv) == 2:
            self.btaddr = sys.argv[1]
        else:
            self.btaddr = "B8:AE:6E:1B:A3:9B"
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

    def process(self, **kwds):
        size = int(self.ctrls['size'].value())
        buffersize = size
        self._buffer = np.append(self._buffer, kwds['dataIn'])
        self._buffer = self._buffer[-size:]
        output = self._buffer
        return {'dataOut': output}

fclib.registerNodeType(BufferNode, [('Data',)])


###############################################################################
class ConvolutionNode(CtrlNode):
    """
    Filters data with square convolution.
    A spinbox widget allows for setting the size of the square.
    """
    nodeName = "Convolution"
    uiTemplate = [
        ('size',  'spin', {'value': convolutionSize,
                           'step': 2,
                           'range': [0, 20]}),
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
    """
    Converts time of sensor inputs to frequency with a fast fourier transform.
    """
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
        print data
        Fs = int(self.bufferSize)
        n = len(data)
        k = np.arange(n)
        T = n/Fs
        frq = k/T
        frq = frq[range(n/2)]
        Y = np.fft.fft(data)/n
        Y = Y[range(n/2)]
        return {'dataOut': abs(Y)}

fclib.registerNodeType(FftNode, [('Data',)])


###############################################################################
class PlotNode(Node):
    """
    Node that hosts a PyQt PlotWidget and in this case,
    two curves for the raw data and the filtered data.
    The raw data is displayed yellow, the filtered is red.
    """
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
    """
    Receives filtered sensor data and data from fft to calculate
    the current activity.
    """
    nodeName = 'Activity'

    def __init__(self, name):
        terminals = {
            'xFilterIn': dict(io='in'),
            'yFilterIn': dict(io='in'),
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
        self.measuredActivities = []
        self.countedActivities = []
        self.label = None
        Node.__init__(self, name, terminals)

    def setLabel(self, label):
        self.label = label
        self.label.setStyleSheet("font: 24pt; color:#33a;")

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

        if(len(self.lastMeanYFft) < 100):
            self.label.setText("Collecting data...")
        else:
            mA = self.measuredActivities

            # check if sitting:
            if(0.0 <= np.mean(self.lastMeanYFft)
               and np.mean(self.lastMeanYFft) <= 14.0):
                        mA.append('sitting')

            # check if standing:
            if(14.0 <= np.mean(self.lastMeanYFft)
               and np.mean(self.lastMeanYFft) <= 15.5
               and 12.4 <= np.mean(self.lastMeanZFft)
               and np.mean(self.lastMeanZFft) <= 13.5):
                        mA.append('standing')

            # check if walking:
            if(14.0 <= np.mean(self.lastMeanYFft)
               and np.mean(self.lastMeanYFft) <= 15.5
               and 11.0 <= np.mean(self.lastMeanZFft)
               and np.mean(self.lastMeanZFft) <= 12.4):
                        mA.append('walking')

            # check if running:
            if(15.5 <= np.mean(self.lastMeanYFft)
               and np.mean(self.lastMeanYFft) <= 17.0):
                        mA.append('running')

            # collect more data to recognise activities more reliable
            # therefore alternating activities aren't recognised right away
            if(len(mA) > 99):
                # cut off old data
                mA = mA[-self.bufferSize:]

                # create dict with key:value pairs,
                # where value is the occurence of a key
                activityDict = dict((i, mA.count(i)) for i in mA)

                # split keys and values into seperate lists
                activityValues = list(activityDict.values())
                activityKeys = list(activityDict.keys())

                text = activityKeys[activityValues.index(max(activityValues))]
                self.label.setText(text)

fclib.registerNodeType(ActivityNode, [('Display',)])


###############################################################################
if __name__ == '__main__':
    import sys
    app = QtGui.QApplication([])
    win = QtGui.QMainWindow()
    win.setWindowTitle('Activity tracker')
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

    # wiimote node
    wiimoteNode = fc.createNode('Wiimote', pos=(0, -300), )

    # X
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
    xConvFftNode = fc.createNode('Fft', pos=(600, -450))
    # plotting fft data of X
    xFftPlotWidget = pg.PlotWidget()
    layout.addWidget(xFftPlotWidget, 0, 2)
    xFftPlotWidget.setYRange(0, 150)
    xFftPlotNode = fc.createNode('PlotWidget', pos=(750, -450))
    xFftPlotNode.setPlot(xFftPlotWidget)
    xFftPlotLegend = pg.LegendItem(offset=(-1, 1))
    xFftPlotLegend.addItem(xFftPlotWidget.getPlotItem().plot(), 'Fft X')
    xFftPlotLegend.setParentItem(xFftPlotWidget.getPlotItem())
    # connecting nodes
    fc.connectTerminals(wiimoteNode['accelX'], xBufferNode['dataIn'])
    fc.connectTerminals(xBufferNode['dataOut'], xConvNode['dataIn'])
    fc.connectTerminals(xBufferNode['dataOut'], xPlotNode1['rawIn'])
    fc.connectTerminals(xConvNode['convolution'], xPlotNode1['filterIn'])
    fc.connectTerminals(xConvNode['convolution'], xConvFftNode['dataIn'])
    fc.connectTerminals(xConvFftNode['dataOut'], xFftPlotNode['In'])

    # Y
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
    yConvFftNode = fc.createNode('Fft', pos=(600, -300))
    # plotting fft data of Y
    yFftPlotWidget = pg.PlotWidget()
    layout.addWidget(yFftPlotWidget, 1, 2)
    yFftPlotWidget.setYRange(0, 150)
    yFftPlotNode = fc.createNode('PlotWidget', pos=(750, -300))
    yFftPlotNode.setPlot(yFftPlotWidget)
    yFftPlotLegend = pg.LegendItem(offset=(-1, 1))
    yFftPlotLegend.addItem(yFftPlotWidget.getPlotItem().plot(), 'Fft Y')
    yFftPlotLegend.setParentItem(yFftPlotWidget.getPlotItem())
    # connecting nodes
    fc.connectTerminals(wiimoteNode['accelY'], yBufferNode['dataIn'])
    fc.connectTerminals(yBufferNode['dataOut'], yConvNode['dataIn'])
    fc.connectTerminals(yBufferNode['dataOut'], yPlotNode1['rawIn'])
    fc.connectTerminals(yConvNode['convolution'], yPlotNode1['filterIn'])
    fc.connectTerminals(yConvNode['convolution'], yConvFftNode['dataIn'])
    fc.connectTerminals(yConvFftNode['dataOut'], yFftPlotNode['In'])

    # Z
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
    zConvFftNode = fc.createNode('Fft', pos=(600, -150))
    # plotting fft data of Z
    zFftPlotWidget = pg.PlotWidget()
    layout.addWidget(zFftPlotWidget, 2, 2)
    zFftPlotWidget.setYRange(0, 150)
    zFftPlotNode = fc.createNode('PlotWidget', pos=(750, -150))
    zFftPlotNode.setPlot(zFftPlotWidget)
    zFftPlotLegend = pg.LegendItem(offset=(-1, 1))
    zFftPlotLegend.addItem(zFftPlotWidget.getPlotItem().plot(), 'Fft Z')
    zFftPlotLegend.setParentItem(zFftPlotWidget.getPlotItem())
    # connecting nodes
    fc.connectTerminals(wiimoteNode['accelZ'], zBufferNode['dataIn'])
    fc.connectTerminals(zBufferNode['dataOut'], zConvNode['dataIn'])
    fc.connectTerminals(zBufferNode['dataOut'], zPlotNode1['rawIn'])
    fc.connectTerminals(zConvNode['convolution'], zPlotNode1['filterIn'])
    fc.connectTerminals(zConvNode['convolution'], zConvFftNode['dataIn'])
    fc.connectTerminals(zConvFftNode['dataOut'], zFftPlotNode['In'])

    # ACTIVITY
    # creating activity tracker
    activity = fc.createNode('Activity', pos=(750, 0))
    activityLabel = QtGui.QLabel("please connect WiiMote")
    layout.addWidget(activityLabel, 2, 0)
    activity.setLabel(activityLabel)
    # connecting nodes
    fc.connectTerminals(xConvFftNode['dataOut'], activity['xFilterIn'])
    fc.connectTerminals(yConvFftNode['dataOut'], activity['yFilterIn'])
    fc.connectTerminals(zConvFftNode['dataOut'], activity['zFilterIn'])

    win.show()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
