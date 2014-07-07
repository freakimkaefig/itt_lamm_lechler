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
import os
import sys


# initial values
bufferSize = 100


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
            print "wiimote connected"
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
class FileReaderNode(CtrlNode):
    """
    Buffers the last n samples provided on input and provides them as a list of
    length n on output.
    A spinbox widget allows for setting the size of the buffer.
    Default size is 32 samples.
    """
    nodeName = "FileReader"
    uiTemplate = [
        ('size',  'spin', {'value': fileName, 'step': 2, 'range': [0, 128]}),
    ]

    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),
            'XdataOut': dict(io='out'),
            'YdataOut': dict(io='out'),
            'ZdataOut': dict(io='out'),
        }
        self._buffer = np.array([])

        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, **kwds):
        #print "cur dir: ",os.path.dirname(os.path.realpath(__file__))
        curdir = os.path.dirname(os.path.realpath(__file__))
        filenames = os.listdir(curdir)
        csvs = [ filename for filename in filenames if filename.endswith( ".csv" ) ]
        
        # logfile = open(str(iteration)+"daten.csv", "a")
        ######## TODO ########
        # alle csv's standardisieren und speichern
        # an fft weitereichen
        # für jeden datensatz (für jede eingehende csv; jede der drei achsen;) fft's berechnen und speichern
        #  samples limitieren
        # x + y + z zusammenhängen
        # (learn / fit() ) -> SVM -> vorhersage (Class X)
        # lernen beim starten durch classifierNode
        # live daten aus buffernode (standardisieren und fft): vorhersage welche activity

fclib.registerNodeType(CSVNode, [('Data',)])

###############################################################################
class SvmClassifierNode (Node):
    nodeName = "SvmClassifier"
    """
    Converts time of sensor inputs to frequency with a fast fourier transform.
    """
    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),
            'dataOut': dict(io='out')
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

fclib.registerNodeType(FftNode, [('Data',)])


###############################################################################
class CategoryVisualizerNode(Node):
    """
    Node that hosts a PyQt PlotWidget and in this case,
    two curves for the raw data and the filtered data.
    The raw data is displayed yellow, the filtered is red.
    """
    nodeName = 'CategoryVisualizer'

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
        self.legend.setParentItem(self.plotWidget.getPlotItem())
        
    def setLabel(self, label):
        self.label = label
        self.label.setStyleSheet("font: 24pt; color:#33a;")

    def process(self, **kwds):
        self.curveRaw.setData(kwds['rawIn'])
        self.curveFilter.setData(kwds['filterIn'])

fclib.registerNodeType(PlotNode, [('Display',)])

###############################################################################

if __name__ == '__main__':
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
    wiimoteNode.connect_wiimote()

    win.show()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
