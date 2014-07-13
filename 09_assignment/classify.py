#!/usr/bin/env python
# coding: utf-8
# -*- coding: utf-8 -*-

"""
This program predicts activities while acting with the wiimote.
It reads csv training data from the '/trainingdata/' directory
or given on text input of the FileReaderNode.
Once the implemented support vector machine is trained with data
it can predict what you're currently doing with the wiimote.

The movements implemented in this version are:
  - sitting: sitting on a chair with the wiimote in the pocket
  - walking: walking with the wiimote in the pocket
  - hopping: hopping rapidly with the wiimote in the pocket
"""


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
from sklearn import svm


# initial values
# for ease of use, the buffers aren't adjustable
size = 100
########################################################################


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
        ('size',  'spin', {'value': size, 'step': 0, 'range': [0, 500]}),
        # buffer fixed for ease of use -----------^
    ]

    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),
            'dataOut': dict(io='out'),
        }
        self._size = np.array([])

        CtrlNode.__init__(self, name, terminals=terminals)

    def process(self, **kwds):
        size = int(self.ctrls['size'].value())
        size = size
        self._size = np.append(self._size, kwds['dataIn'])
        self._size = self._size[-(size):]
        output = self._size
        return {'dataOut': output}

fclib.registerNodeType(BufferNode, [('Data',)])


###############################################################################
class MergeNode(Node):
    """
    Merges the sizeed data of all three axis (x, y, z) into one list of
    average values and outputs it.
    """
    nodeName = "Merge"

    def __init__(self, name):
        terminals = {
            'xIn': dict(io='in'),
            'yIn': dict(io='in'),
            'zIn': dict(io='in'),
            'dataOut': dict(io='out'),
        }
        self._size = []

        Node.__init__(self, name, terminals=terminals)

    def process(self, **kwds):
        self._size = []
        self._size.append((kwds['xIn'] + kwds['yIn'] + kwds['zIn']) / 3)
        return {'dataOut': self._size}

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

        self.size = size

        Node.__init__(self, name, terminals=terminals)

    def process(self, **kwds):
        out = [np.abs(fft(l)/len(l))[1:len(l)/2] for l in kwds['dataIn']]

        return {'dataOut': out}

fclib.registerNodeType(FftNode, [('Data',)])


###############################################################################
class FileReaderNode(CtrlNode):
    """
    Reads training data from csv files in the directory 'trainingdata'
    and outputs the read data on one output
    as well as the related activities on another output.
    """
    nodeName = "FileReader"

    def __init__(self, name):
        terminals = {
            'categoryOut': dict(io='out'),
            'dataOut': dict(io='out'),
        }

        self.trainingData = []
        self.categories = []
        self.directory = '/trainingdata/'

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

    # receives an array of data
    # cuts it to the same length as the buffers
    # and returns it
    def cut_to_same_size(self, data):
        cutted_data = []
        minlen = size
        for x in data:
            if len(x) >= minlen:
                cutted_data.append(x[-minlen:])
        return cutted_data

    # reads csv data of the given file
    # and returns array of mean values
    def read_data(self, filename):
        x = []
        y = []
        z = []
        avg = []
        els = []
        for line in open(filename, "r").readlines():
            # check for proper file-structure
            if(len(line.strip().split(",")) == 3):
                _x, _y, _z = map(int, line.strip().split(","))
            x.append(_x)
            y.append(_y)
            z.append(_z)
            avg.append((_x+_y+_z)/3)
        return avg

    def checkDirectory(self):
        # get all file names in self.directory
        filenames = os.listdir(self.directory.replace('/', ''))
        for filename in filenames:
            # receive category name from filename
            category = ''.join([i for i in filename if not i.isdigit()])
            category = category.replace('.csv', '')
            self.categories.append(category)
            # set training data
            data = self.read_data(self.curdir+self.directory+filename)
            self.trainingData.append(data)

        self.trainingData = self.cut_to_same_size(self.trainingData)
        self.update()
        self.clear()

    def readFiles(self):
        self.clear()
        self.text.setStyleSheet('color:black')
        # manual import:
        _file = str(self.text.text()).strip()
        if _file != '':  # if text input of node isn't empty
            if os.path.isfile(_file):  # check if file exists
                self.text.setStyleSheet('color:green')  # visual feedback
                # extract category name from filename (Pattern: activity1.csv)
                category = _file[_file.find("/")+1:_file.find(".")]
                category = ''.join([i for i in category if not i.isdigit()])
                category = category.replace('.csv', '')
                # set training data and categories
                data = self.read_data(self.curdir+'/'+_file)
                self.categories.append(category)
                self.trainingData.append(data)
            else:
                # set text color to red -> file doesn't exist
                self.text.setStyleSheet('color:red')

        self.trainingData = self.cut_to_same_size(self.trainingData)
        self.update()
        self.clear()

    def clear(self):
        self.trainingData = []
        self.categories = []
        self.update()

    def process(self):
        return {'dataOut': self.trainingData, 'categoryOut': self.categories}


fclib.registerNodeType(FileReaderNode, [('Data',)])


###############################################################################
class SvmClassifierNode (Node):
    nodeName = "SvmClassifier"
    """
    The core of the SvmClassifierNode is a support vector machine.
    It is trained by data on the 'dataIn'-Input with the related activities
    on the 'categoryIn'-Input.
    The support vector machine compares the live data on the
    'classifyIn'-Input with the trained activities and outputs a prediction
    on the 'prediction'-Output
    """
    def __init__(self, name):
        terminals = {
            'dataIn': dict(io='in'),
            'categoryIn': dict(io='in'),
            'classifyIn': dict(io='in'),
            'prediction': dict(io='out'),
        }

        self.classifier = svm.SVC()
        self.prediction = []
        self.oldData = []

        Node.__init__(self, name, terminals=terminals)

    def process(self, **kwds):
        if kwds['dataIn'] and kwds['categoryIn']:
            # train support vector machine
            self.classifier.fit(kwds['dataIn'], kwds['categoryIn'])

        # check if training-data was loaded
        loaded = len(kwds['classifyIn'][0])
        # number of files in trainingdata dir
        load = len(os.listdir('/trainingdata/'.replace('/', '')))
        if loaded >= load:
            # start live recognition
            self.prediction = self.classifier.predict(kwds['classifyIn'])
        else:
            # display status (size is loading)
            self.prediction = []
            status = 'loading training-data: ' + str(loaded) + '/' + str(load)
            self.prediction.append(status)

        return {'prediction': self.prediction}

fclib.registerNodeType(SvmClassifierNode, [('Data',)])


###############################################################################
class CategoryVisualizerNode(Node):
    """
    The CategoryVisualizerNode receives a prediction or a status for displaying
    from the SvmClassifierNode.
    Predictions are displayed based on their occureance within the last 100
    predictions.
    """
    nodeName = 'CategoryVisualizer'

    def __init__(self, name):
        terminals = {
            'categoryIn': dict(io='in')
        }
        Node.__init__(self, name, terminals)

        self.recog = []

    def setLabel(self, label):
        self.label = label
        self.label.setStyleSheet("font: 24pt; color:#33a;")

    def process(self, **kwds):
        # collect data
        self.recog.append(kwds['categoryIn'][0])

        if "loading" not in kwds['categoryIn'][0]:
            if len(self.recog) > size - 1:
                # cut of old data
                self.recog = self.recog[-size:]

                # create dict with key:value pairs,
                # where value is the occurence of a key
                aDict = dict((i, self.recog.count(i)) for i in self.recog)

                # split keys and values into seperate lists
                activityValues = list(aDict.values())
                activityKeys = list(aDict.keys())

                # displayed activity = highest occurence of recognized activity
                # this slows down the recognition process
                # but improves recognition
                text = activityKeys[activityValues.index(max(activityValues))]

                self.label.setText(text)
            else:
                self.label.setText('Collecting data...')

        else:
            self.label.setText(kwds['categoryIn'][0])

fclib.registerNodeType(CategoryVisualizerNode, [('Display',)])


###############################################################################
if __name__ == '__main__':
    print "Press sync on your WiiMote"

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

    # create sizeNodes for each axis
    xBufferNode = fc.createNode('Buffer', pos=(150, 0))
    yBufferNode = fc.createNode('Buffer', pos=(150, 150))
    zBufferNode = fc.createNode('Buffer', pos=(150, -150))

    # mergeNode merges the sizeed data of three axes
    mergeNode = fc.createNode('Merge', pos=(300, 150))

    # fileReader to read csv training data
    fileReader = fc.createNode('FileReader', pos=(300, -150))

    # svmClassifier gets feeded by training data, categories and live data
    svmClassifier = fc.createNode('SvmClassifier', pos=(600, 0))

    # node to display the predicted activity
    display = fc.createNode('CategoryVisualizer', pos=(750, 0))

    # FFT nodes
    liveFft = fc.createNode('Fft', pos=(450, 150))
    trainingFft = fc.createNode('Fft', pos=(450, -150))

    # creating a label for information
    text = "The tool predicts your activity while acting with the wiimote"
    text += "\nbased on trained data and a machine learning algorithm."
    infoText = QtGui.QLabel(text)
    infoText.setStyleSheet("font: 12pt; color:#000;")
    layout.addWidget(infoText, 2, 0)

    # creating label for recognized activity
    activityLabel = QtGui.QLabel("initializing")
    layout.addWidget(activityLabel, 3, 0)
    display.setLabel(activityLabel)

    # connect Nodes
    fc.connectTerminals(wiimoteNode['accelX'], xBufferNode['dataIn'])
    fc.connectTerminals(wiimoteNode['accelY'], yBufferNode['dataIn'])
    fc.connectTerminals(wiimoteNode['accelZ'], zBufferNode['dataIn'])
    # merge x,y,z values
    fc.connectTerminals(xBufferNode['dataOut'], mergeNode['xIn'])
    fc.connectTerminals(yBufferNode['dataOut'], mergeNode['yIn'])
    fc.connectTerminals(zBufferNode['dataOut'], mergeNode['zIn'])
    # fft nodes for live data and training data
    fc.connectTerminals(mergeNode['dataOut'], liveFft['dataIn'])
    fc.connectTerminals(fileReader['dataOut'], trainingFft['dataIn'])
    # connecting support vector machine
    fc.connectTerminals(fileReader['categoryOut'], svmClassifier['categoryIn'])
    fc.connectTerminals(liveFft['dataOut'], svmClassifier['classifyIn'])
    fc.connectTerminals(trainingFft['dataOut'], svmClassifier['dataIn'])
    # connecting visual output of prediction
    fc.connectTerminals(svmClassifier['prediction'], display['categoryIn'])

    # read training data on startup
    fileReader.checkDirectory()

    win.show()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
