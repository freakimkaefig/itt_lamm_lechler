#!/usr/bin/env python
# coding: utf-8
# -*- coding: utf-8 -*-


from pyqtgraph.flowchart import Flowchart, Node
from pyqtgraph.flowchart.library.common import CtrlNode
import pyqtgraph.flowchart.library as fclib
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
from scipy import fft
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
class MergeNode(Node):
    """
    bla
    """
    nodeName = "Merge"

    def __init__(self, name):
        terminals = {
            'xIn': dict(io='in'),
            'yIn': dict(io='in'),
            'zIn': dict(io='in'),
            'dataOut': dict(io='out'),
        }
        self._buffer = np.array([])

        Node.__init__(self, name, terminals=terminals)

    def process(self, **kwds):
        output = ((kwds['xIn'] + kwds['yIn'] + kwds['zIn']) / 3)
        return {'dataOut': output}

fclib.registerNodeType(MergeNode, [('Data',)])

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
        """
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
        """
        output = [np.abs(fft(l)/len(l))[1:len(l)/2] for l in kwds['dataIn']]
        #return {'dataOut': abs(Y)}
        return {'dataOut': output}

fclib.registerNodeType(FftNode, [('Data',)])


###############################################################################

class FileReaderNode(CtrlNode):
    """
    Reads training data
    """
    nodeName = "FileReader"

    def __init__(self, name):
        terminals = {
            'categoryOut': dict(io='out'),
            'dataOut': dict(io='out'),
        }

        self.trainingData = []
        self.categories = []
        self.directory = '/test/'
        
        # get current directory
        self.curdir = os.path.dirname(os.path.realpath("__file__"))

        self.ui = QtGui.QWidget()
        self.layout = QtGui.QGridLayout()

        label = QtGui.QLabel("Filename:")
        self.layout.addWidget(label)
        self.text = QtGui.QLineEdit()
        self.layout.addWidget(self.text)

        self.read_file_button = QtGui.QPushButton("read")
        self.layout.addWidget(self.read_file_button)
        self.ui.setLayout(self.layout)
        self.read_file_button.clicked.connect(self.readFiles)

        
        Node.__init__(self, name, terminals=terminals)

    def read_data(self, filename):
        print filename
        x = []
        y = []
        z = []
        avg = []
        els = []
        for line in open(filename, "r").readlines():
            print line
            # check for proper file-structure
            if(len(line.strip().split(",")) == 3):
                _x, _y, _z = map(int,line.strip().split(","))
            x.append(_x)
            y.append(_y)
            z.append(_z)
            # precompute lists and append to list
            avg.append((_x+_y+_z)/3)
        return avg

    def readFiles(self):
        passed_filename = str(self.text.text()).strip()
        if passed_filename == '':
            filenames = os.listdir(self.directory.replace('/', ''))
            #print filenames
            for filename in filenames:
                category = ''.join([i for i in filename if not i.isdigit()])
                category = category.replace('.csv', '')
                #print category

                self.categories.append(category)
                self.trainingData.append(self.read_data(self.curdir+self.directory+filename))

        else:
            # TODO: check if passed_filename is in curdir!!!

            category = ''.join([i for i in passed_filename if not i.isdigit()])
            category = category.replace('.csv', '')
            # print category
            self.categories.append(category)
            self.trainingData.append(self.read_data(self.curdir+'/'+passed_filename))

        self.update()

    def process(self):
        # print "FileReaderNode.process"
        return {'dataOut': self.trainingData, 'categoryOut': self.categories}


fclib.registerNodeType(FileReaderNode, [('Data',)])

###############################################################################
class SvmClassifierNode (Node):
    nodeName = "SvmClassifier"
    """
    ## TODO
    # explain what this Node does (see wiimoteNode)
    """
    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),
            'categoryIn': dict(io='in'),
            'classifyIn': dict(io='in'),
            'prediction': dict(io='out'),
        }

        self.recognized_category = []

        Node.__init__(self, name, terminals=terminals)

    def process(self, **kwds):
        # print "SvmClassifierNode.process"
        # print kwds['trainingAndCategoryDataIn'][0]['category']
        return {'prediction': self.recognized_category}

fclib.registerNodeType(SvmClassifierNode, [('Data',)])


###############################################################################
class CategoryVisualizerNode(Node):
    """
    ##TODO
    # explain what this Node does (see wiimoteNode)
    """
    nodeName = 'CategoryVisualizer'

    def __init__(self, name):
        terminals = {
            'categoryIn': dict(io='in')
        }
        Node.__init__(self, name, terminals)

        
    def setLabel(self, label):
        self.label = label
        self.label.setStyleSheet("font: 24pt; color:#33a;")

    def process(self, **kwds):
        return

fclib.registerNodeType(CategoryVisualizerNode, [('Display',)])

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
    wiimoteNode = fc.createNode('Wiimote', pos=(0, 0), )
    wiimoteNode.connect_wiimote()
    
    xBufferNode = fc.createNode('Buffer', pos=(150, -150))
    yBufferNode = fc.createNode('Buffer', pos=(150, 0))
    zBufferNode = fc.createNode('Buffer', pos=(150, 150))
    mergeNode = fc.createNode('Merge', pos=(300, 300))
    fileReaderNode = fc.createNode('FileReader', pos=(300, 150))
    svmClassifierNode = fc.createNode('SvmClassifier', pos=(450, 150))
    categoryVisualizerNode = fc.createNode('CategoryVisualizer', pos=(600, 150))

    # FFT nodes
    liveFftNode = fc.createNode('Fft', pos=(450, 300))
    trainingFftNode = fc.createNode('Fft', pos=(150, 300))
    
    # creating label for recognized activity
    activityLabel = QtGui.QLabel("I'm a label")
    layout.addWidget(activityLabel, 2, 0)
    categoryVisualizerNode.setLabel(activityLabel)
    
    # connect Nodes
    fc.connectTerminals(wiimoteNode['accelX'], xBufferNode['dataIn'])
    fc.connectTerminals(wiimoteNode['accelY'], yBufferNode['dataIn'])
    fc.connectTerminals(wiimoteNode['accelZ'], zBufferNode['dataIn'])
    # merge x,y,z values
    fc.connectTerminals(xBufferNode['dataOut'], mergeNode['xIn'])
    fc.connectTerminals(yBufferNode['dataOut'], mergeNode['yIn'])
    fc.connectTerminals(zBufferNode['dataOut'], mergeNode['zIn'])
    # fft nodes for live data
    fc.connectTerminals(mergeNode['dataOut'], liveFftNode['dataIn'])
    fc.connectTerminals(fileReaderNode['dataOut'], trainingFftNode['dataIn'])
    fc.connectTerminals(fileReaderNode['categoryOut'], svmClassifierNode['categoryIn'])

    fc.connectTerminals(liveFftNode['dataOut'], svmClassifierNode['classifyIn'])
    fc.connectTerminals(trainingFftNode['dataOut'], svmClassifierNode['dataIn'])
    
    # fft Node missing between fileReaderNode and svmClassifierNode
    fc.connectTerminals(svmClassifierNode['prediction'], categoryVisualizerNode['categoryIn'])


    #fileReaderNode.readFiles()

    win.show()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
