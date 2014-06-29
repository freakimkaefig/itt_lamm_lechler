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
import math
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
        ('size',  'spin', {'value': 4.0, 'step': 1.0, 'range': [0.0, 128.0]}),
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

    def register_buttons(self, buttons):
        self.buttons = buttons
        self.buttons.register_callback(self.button_callback)

    def button_callback(self, buttons):
        if buttons:
            if buttons[0] == ('Minus', True):
                self.decrease_buffer_size()
            if buttons[0] == ('Plus', True):
                self.increase_buffer_size()

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

        if self.buttons is None:
            self.register_buttons(kwds['buttons'])

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
            'templateIn': dict(io='in'),
        }
        self._ir_vals = []
        self._xy_vals = []
        self.plot = None
        self.spiPos = None
        self.spiPath = None
        self.spiTemplate = None
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
        if vals == []:
            self.spiPath.clear()
        else:
            points = []
            counter = 1
            for point in vals:
                points.append({'pos': [1024 - point[0], 768 - point[1]], 'data': counter})
                counter += 1
            self.spiPath.addPoints(points)
            self.plot.addItem(self.spiPath)

    def plotTemplate(self, vals):
        # plotting recognized template
        if vals == []:
            self.spiTemplate.clear()
        else:
            points = []
            counter = 1
            for point in vals:
                points.append({'pos': [1024 - point[0], 768 - point[1]], 'data': counter})
                counter += 1
            self.spiTemplate.addPoints(points)
            self.plot.addItem(self.spiTemplate)

    def setPlot(self, plot):
        self.plot = plot
        self.spiPos = pg.ScatterPlotItem(size=3, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 255))
        self.spiPath = pg.ScatterPlotItem(size=3, pen=pg.mkPen(None), brush=pg.mkBrush(255, 0, 0, 255))
        self.spiTemplate = pg.ScatterPlotItem(size=3, pen=pg.mkPen(None), brush=pg.mkBrush(0, 100, 255, 255))

        self.plot.setXRange(0, 1024)
        self.plot.setYRange(0, 768)

        self.legend = pg.LegendItem(offset=(-1, 1))
        self.legend.addItem(self.spiPos, 'position')
        self.legend.addItem(self.spiPath, 'path')
        self.legend.addItem(self.spiTemplate, 'template')
        self.legend.setParentItem(self.plot)

    def process(self, **kwds):
        self.plotPosition(kwds['positionIn'])
        self.plotPath(kwds['pathIn'])
        self.plotTemplate(kwds['templateIn'])

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
            'pathOut': dict(io='out'),
            'templateOut': dict(io='out'),
        }
        self.path = []
        self.recognizedTemplate = []

        self.inputVals = None
        self.buttons = None
        self.aPressed = False
        self.bPressed = False
        self.once = 0

        self.templates = []
        self.templateCounter = 0
        self.SQUARE_SIZE = 250.0
        self.HALF_DIAGONAL = 0.5 * math.sqrt(250.0 * 250.0 + 250.0 * 250.0)
        self.ANGLE_RANGE = 45.0
        self.ANGLE_PRECISION = 2.0
        self.PHI = 0.5 * (-1.0 + math.sqrt(5.0))  # Golden Ratio

        Node.__init__(self, name, terminals=terminals)

    def register_buttons(self, buttons):
        self.buttons = buttons
        self.buttons.register_callback(self.button_callback)

    def button_callback(self, buttons):
        if buttons:
            if buttons[0] == ('A', True):
                self.recognizedTemplate = []
                self.aPressed = True
                self.recordGesture()
            if buttons[0] == ('A', False):
                if self.aPressed:
                    self.aPressed = False
                    template = self.checkRecognizedGesture(self.path)
                    self.label.setText(template[0] + " | " + str(template[1]))
                    self.path = []

            if buttons[0] == ('B', True):
                self.recognizedTemplate = []
                self.bPressed = True
                self.recordGesture()
            if buttons[0] == ('B', False):
                if self.bPressed:
                    self.bPressed = False
                    """
                    # öffnet input dialog -> error (threads und so kack)
                    name = inputDialog()
                    if name is False:
                        return
                    """
                    name = "TEMPLATE" + str(self.templateCounter)
                    self.addTemplate(name, self.path)
                    self.templateCounter += 1
                    self.path = []

    def setLabel(self, label):
        self.label = label
        self.label.setStyleSheet("font: 24pt; color:#33a;")


    class Template:
        """A gesture template. Used internally by Recognizer."""
        def __init__(self, name, points):
            """'name' is a label identifying this gesture, and 'points' is a list of tuple co-ordinates representing the gesture positions. Example: [(1, 10), (3, 8) ...]"""
            self.name = name
            self.points = points

    """
    Helper functions
    """
    def distance(self, x, y):
        dx = x[0] - y[0]
        dy = x[1] - y[1]
        distance = math.sqrt(abs(dx*dx - dy*dy))
        return distance

    def total_length(self, point_list):
        p1 = point_list[0]
        length = 0.0
        for i in range(1, len(point_list)):
            length += self.distance(p1, point_list[i])
            p1 = point_list[i]
        return length

    def _centroid(self, points):
        """Returns the centre of a given set of points."""
        x = 0.0
        y = 0.0
        for point in points:
            x += point[0]
            y += point[1]
        x /= len(points)
        y /= len(points)
        return (x, y)


    def _rotateBy(self, points, theta):
        """Rotate a set of points by a given angle."""
        c = self._centroid(points);
        cos = math.cos(theta);
        sin = math.sin(theta);
   
        newpoints = [];
        for point in points:
            qx = (point[0] - c[0]) * cos - (point[1] - c[1]) * sin + c[0]
            qy = (point[0] - c[0]) * sin + (point[1] - c[1]) * cos + c[1]
            newpoints.append((qx, qy))
        return newpoints

    def _boundingBox(self, points):
        """Returns a Rectangle representing the bounding box that contains the given set of points."""
        minX = float("+Infinity")
        maxX = float("-Infinity")
        minY = float("+Infinity")
        maxY = float("-Infinity")

        for point in points:
            if point[0] < minX:
                minX = point[0]
            if point[0] > maxX:
                maxX = point[0]
            if point[1] < minY:
                minY = point[1]
            if point[1] > maxY:
                maxY = point[1]
        return (minX, minY, maxX - minX, maxY - minY)

    def _pathDistance(self, pts1, pts2):
        """'Distance' between two paths."""
        d = 0.0;
        length = 0

        if len(pts1) > len(pts2):
            length = len(pts2)
        else:
            length = len(pts1)

        """
        hier is evtl noch n fehler.
        keine ahnung ob man das machen kann, aber wir haben ja nicht immer die gleiche anzahl
        an punkten, wie im template
        """
        # for index in range(len(pts1)):  # assumes pts1.length == pts2.length
        for index in range(length):
            d += self.distance(pts1[index], pts2[index])
        return d / len(pts1)

    def _distanceAtAngle(self, points, T, theta):
        """Returns the distance by which a set of points differs from a template when rotated by theta."""
        newpoints = self._rotateBy(points, theta)
        return self._pathDistance(newpoints, T.points)

    def _distanceAtBestAngle(self, points, T, a, b, threshold):
        """Search for the best match between a set of points and a template, using a set of tolerances. Returns a float representing this minimum distance."""
        x1 = self.PHI * a + (1.0 - self.PHI) * b
        f1 = self._distanceAtAngle(points, T, x1)
        x2 = (1.0 - self.PHI) * a + self.PHI * b
        f2 = self._distanceAtAngle(points, T, x2)

        while abs(b - a) > threshold:
            if f1 < f2:
                b = x2
                x2 = x1
                f2 = f1
                x1 = self.PHI * a + (1.0 - self.PHI) * b
                f1 = self._distanceAtAngle(points, T, x1)
            else:
                a = x1
                x1 = x2
                f1 = f2
                x2 = (1.0 - self.PHI) * a + self.PHI * b
                f2 = self._distanceAtAngle(points, T, x2)
        return min(f1, f2)

    """
    Functions of $1 recognizer
    Based on project dollar from: http://sleepygeek.org/projects.dollar
    """
    def resample(self, point_list, step_count=64):
        newpoints = []
        length = self.total_length(point_list)
        stepsize = length/step_count
        curpos = 0
        newpoints.append(point_list[0])
        i = 1
        while i < len(point_list):
            p1 = point_list[i-1]
            d = self.distance(p1, point_list[i])
            if curpos + d >= stepsize:
                nx = p1[0] + ((stepsize - curpos) / d) * (point_list[i][0] - p1[0])
                ny = p1[1] + ((stepsize - curpos) / d) * (point_list[i][1] - p1[1])
                newpoints.append([nx, ny])
                point_list.insert(i, [nx, ny])
                curpos = 0
            else:
                curpos += d
            i += 1
        if(self.once == 0):
            self.once = 1
        return newpoints

    def _rotateToZero(self, points):
        """Rotate a set of points such that the angle between the first point and the centre point is 0."""
        c = self._centroid(points)
        theta = math.atan2(c[1] - points[0][1], c[0] - points[0][0])
        return self._rotateBy(points, -theta)

    def _scaleToSquare(self, points, size):
        """Scale a scale of points to fit a given bounding box."""
        B = self._boundingBox(points)
        newpoints = []
        for point in points:
            qx = point[0] * (size / B[2])
            qy = point[1] * (size / B[3])
            newpoints.append((qx, qy))
        return newpoints

    def _translateToOrigin(self, points):
        """Translate a set of points, placing the centre point at the origin."""
        c = self._centroid(points)
        newpoints = []
        for point in points:
            qx = point[0] - c[0]
            qy = point[1] - c[1]
            newpoints.append((qx, qy))
        return newpoints;

    # starting point for gesture recognition, after path is saved
    def checkRecognizedGesture(self, path):
        # uses $1 recognizer functions
        print "1: ", path[0]
        path = self.resample(path, len(path))
        print "2: ", path[0]
        path = self._rotateToZero(path)
        print "3: ", path[0]
        path = self._scaleToSquare(path, self.SQUARE_SIZE)
        print "4: ", path[0]
        path = self._translateToOrigin(path);
        print "5: ", path[0]

        bestDistance = float("infinity")
        bestTemplate = None
        for template in self.templates:
            distance = self._distanceAtBestAngle(path, template, -self.ANGLE_RANGE, +self.ANGLE_RANGE, self.ANGLE_PRECISION)
            if distance < bestDistance:
                bestDistance = distance
                bestTemplate = template
                self.recognizedTemplate = bestTemplate.points

        score = 1.0 - (bestDistance / self.HALF_DIAGONAL)
        return (bestTemplate.name, score)

    # function to save gesture, while A-Button is pressed
    def recordGesture(self):
        self.path.append(self.inputVals)

    def addTemplate(self, name, points):
        points = self.resample(points)
        points = self._rotateToZero(points)
        points = self._scaleToSquare(points, self.SQUARE_SIZE)
        points = self._translateToOrigin(points)
        self.templates.append(self.Template(name, points))

        print "Added Template", name

    def process(self, **kwds):
        if self.buttons is None:
            self.register_buttons(kwds['buttons'])

        self.inputVals = kwds['In']

        if self.aPressed:
            self.recordGesture()

        if self.bPressed:
            self.recordGesture()

        return {'pathOut': self.path, 'templateOut': self.recognizedTemplate}

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
    fc.connectTerminals(gestureNode['pathOut'], gesturePlotNode['pathIn'])
    fc.connectTerminals(gestureNode['templateOut'], gesturePlotNode['templateIn'])

    def inputDialog():
        (name, ok) = QtGui.QInputDialog.getText(cw, "TEXT", "Name: ", QtGui.QLineEdit.Normal, "value")
        if ok is False:
            return False
        else:
            value = str(value)
            return value

    win.show()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()


"""
TODO:
-----

    Das erkannte Template wird noch an der falschen Position ausgegeben (immer rechts oben im Eck).

    DialogBox zum eingeben eines Namens für ein Template produziert Thread-Fehler (Zeile 372)
    Anhaltspunkt für Dialogboxen: Zeile 657
    http://pyqt.sourceforge.net/Docs/PyQt4/qinputdialog.html
    http://nullege.com/codes/search/PyQt4.QtGui.QInputDialog.getText

    In der Methode _pathDistance (Zeile 454) musste ich was ändern, wo ich mir nicht sicher bin, ob des so geht.

    Drei Start-Templates müssen noch angelegt werden.

    Score für Übereinstimmung des Templates im Label muss noch ausgeblendet werden (evtl hier n Schwellenwert, muss aber auch nicht).

    Print Ausgaben in checkRecognizedGesture (Zeile 555) und addTemplate (Zeile 590) rausnehmen

    Quelle zu 1$-Recognizer evtl deutlicher angeben.
    http://sleepygeek.org/svn_public/wsvn/dollar_recognizer/dollar.py?op=file
"""