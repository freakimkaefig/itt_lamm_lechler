#!/usr/bin/env python
# coding: utf-8
# -*- coding: utf-8 -*-

"""
This tool is used to detect user input in terms of performed gestures with a
wiimote. The data of all three axes is measured and interpreted to determin
 three predefined gestures (triangle, rectangle and circle). To perform a
gesture which will be displayed on the screen, one has to press the ‘A’ button
while moving the wiimote. It is also possible to create own gesture templates
by pressing the ‘B’ button while performing a gesture.
Those created templates will be named ‘My Custom Template X’.
Where X is an increasing number starting at ‘0’.
Once templates are created the tool is able to recognize those gestures.
Detected gestures are displayed at the bottom of the tool followed by its
computed precision.
Disturbances may occure if a created template isn’t varying enough of other
templates. Another possible issure can occure if the performed gesture
isn’t accurate enough.
Some methods are based on the $1 recognizer to detect gestures:
http://sleepygeek.org/projects.dollar
Some minor adjustments were made in a few of those methods.
"""

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
                t = "Press 'A' to start gesture or 'B' to record"
                gestureLabel.setText(t)
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
        """calculates most intense light source"""
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
        self.pathVals = []
        self.spiTemplate = None
        self.templateVals = []
        self.avg_val = (0, 0)

        Node.__init__(self, name, terminals=terminals)

    def plotPosition(self, val):
        """plotting current position of the "pointer" (ir light source)"""
        if val is not None:
            self.spiPos.clear()
            points = [{'pos': [1024 - val[0], 768 - val[1]], 'data': 1}]
            self.spiPos.addPoints(points)
            self.plot.addItem(self.spiPos)

    def plotPath(self, vals):
        """plotting path while recording (visual feedback)"""
        if vals == []:
            self.spiPath.clear()
        else:
            points = []
            counter = 1
            for point in vals:
                points.append({'pos': [1024 - point[0],
                                       768 - point[1]], 'data': counter})
                counter += 1
            self.spiPath.addPoints(points)
            self.plot.addItem(self.spiPath)

    def plotTemplate(self, vals):
        """plotting recognized template"""
        if vals == []:
            self.spiTemplate.clear()
        if self.templateVals == vals:
            # if template stays the same, do nothing (performance reasons)
            return
        else:
            self.templateVals = vals
            points = []
            counter = 1
            for point in vals:
                points.append({'pos': [512 - point[0],
                                       384 - point[1]], 'data': counter})
                counter += 1
            self.spiTemplate.addPoints(points)
            self.plot.addItem(self.spiTemplate)

    def setPlot(self, plot):
        """setting the ScatterPlotWidget for the node"""
        self.plot = plot

        # ScatterPlotItem for the current position of the 'Pointer'
        self.spiPos = pg.ScatterPlotItem(size=3,
                                         pen=pg.mkPen(None),
                                         brush=pg.mkBrush(255, 255, 255, 255))

        # ScatterPlotItem for the path, while drawing
        self.spiPath = pg.ScatterPlotItem(size=3,
                                          pen=pg.mkPen(None),
                                          brush=pg.mkBrush(255, 0, 0, 255))

        # ScatterPlotItem for the recognized template
        self.spiTemplate = pg.ScatterPlotItem(size=3,
                                              pen=pg.mkPen(None),
                                              brush=pg.mkBrush(0,
                                                               100, 255, 255))

        # setting the x and y range to width and height of the ir camera field
        self.plot.setXRange(0, 1024)
        self.plot.setYRange(0, 768)

        # appending legend to display which color shows which data
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
    Handles gesture recognition of point data from wiimote ir camera
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
        self.templateCounter = 1

        # constant values for templates and $1 recognizer
        self.TEMPLATE_NAME = "My Custom Template "
        self.SQUARE_SIZE = 250.0
        self.HALF_DIAGONAL = 0.5 * math.sqrt(250.0 * 250.0 + 250.0 * 250.0)
        self.ANGLE_RANGE = 45.0
        self.ANGLE_PRECISION = 2.0
        self.PHI = 0.5 * (-1.0 + math.sqrt(5.0))  # Golden Ratio

        """own templates"""
        # points for rectangle
        t1 = [(-119.79861641283537, 2.2737367544323206e-13),
              (-121.66758236738212, -12.174424362903551),
              (-117.04135107505294, -23.5980131263359),
              (-111.33780556140186, -33.463130392462745),
              (-104.77577255593565, -42.41631206839054),
              (-97.07071187094584, -50.280083868437146),
              (-89.44636330582068, -58.2051803901727),
              (-81.8968126811435, -66.19078602048012),
              (-74.85263892767182, -74.59338603935544),
              (-67.79235657389506, -82.9818054579896),
              (-60.70952868308757, -91.35037776130616),
              (-52.612746628355694, -98.9448292580364),
              (-44.551009564383435, -106.55333822288424),
              (-37.98841378599559, -115.56699243591174),
              (-30.5317890269896, -124.2200587005284),
              (-19.077538114091, -120.79512435978808),
              (-10.866155018218933, -113.82413760451664),
              (-3.118794477497204, -106.28910953260561),
              (4.557927967380806, -98.65967222625011),
              (12.173287575644963, -90.94822225578116),
              (20.220454005466536, -83.76495532721196),
              (28.58569286133377, -76.97075233451858),
              (37.11828984916019, -70.34953233996396),
              (45.96114880405014, -64.04900214185284),
              (54.80400775894009, -57.74847194374183),
              (63.594494453259585, -51.39655860530411),
              (72.36787843385969, -45.027865560788655),
              (81.10783193674035, -38.6255774007069),
              (89.75756051282815, -32.13261997565007),
              (98.36059526820134, -25.588731145893348),
              (106.50668968495847, -18.54643346987814),
              (114.6010909481871, -11.435094744543562),
              (121.856394282314, -3.2030621254749576),
              (128.2579728996243, 6.862337283444731),
              (127.43952047078562, 19.963353956798528),
              (117.6302879674189, 26.697040933711378),
              (105.72724735857082, 32.588776682698835),
              (95.90695402125152, 39.19912556179747),
              (88.63496473233477, 47.41918322567324),
              (81.451053940316, 55.70057127374878),
              (74.35725827119006, 64.0595491245623),
              (67.35518018231687, 72.49994372434594),
              (62.283553561472786, 83.55953159628586),
              (59.585057159855864, 100.28352817474524),
              (52.55981844711448, 109.1315119733166),
              (43.31829802682569, 116.0369085250012),
              (32.724772780330795, 122.38162655170413),
              (17.987992364201205, 125.7799412994716),
              (6.976522018166179, 120.23916990247858),
              (-1.0655110882386225, 113.0708848814229),
              (-8.725689921841763, 105.42014222099544),
              (-16.38586875544479, 97.76939956056776),
              (-24.0802959703135, 90.1627559374092),
              (-32.03152160306911, 82.88677211720983),
              (-39.982747235824604, 75.61078829701057),
              (-47.93397286858044, 68.33480447681131),
              (-56.003397790835606, 61.193181682648856),
              (-64.54545168534219, 54.58881181035508),
              (-73.08750557984865, 47.98444193806097),
              (-81.62955947435512, 41.380072065767195),
              (-90.62192576810355, 35.181212612542254),
              (-100.47342094644148, 29.756006548854543),
              (-110.32491612477929, 24.330800485166947),
              (-121.74202710037571, 19.82146677507444)]
        self.templates.append(self.Template("Rectangle", t1))

        # points for circle
        t2 = [(-101.78312058310325, 5.684341886080802e-14),
              (-99.45527922494529, -10.058286326024074),
              (-95.84608839049207, -20.100034342039294),
              (-91.7897353856107, -30.16496520724104),
              (-87.19455584834645, -40.325751793013126),
              (-82.3841145946401, -50.52483283108245),
              (-77.50779323322593, -60.74071830092879),
              (-72.01361130182579, -71.11420514935998),
              (-66.51942937042571, -81.48769199779127),
              (-60.178755282542, -92.18385833201353),
              (-52.46764663401149, -103.40242893891912),
              (-39.57790673140147, -118.1330075551158),
              (-25.420862180832728, -127.94154905619348),
              (-14.870718165057951, -132.28617148533579),
              (-6.282891467456125, -132.6893032124999),
              (2.304935230145702, -133.09243493966386),
              (10.576694788603504, -132.28418036397676),
              (18.694261163724832, -130.88495163389774),
              (26.808742019104216, -129.45571385726947),
              (34.71153749237135, -125.96767334496803),
              (42.61433296563848, -122.47963283266665),
              (50.538351209309894, -118.59787882465417),
              (58.568848497475756, -112.74078248247594),
              (66.59934578564162, -106.8836861402977),
              (76.24114750748834, -95.22146464749),
              (85.87521859915842, -78.50162409690711),
              (93.37404574789855, -59.96771285265385),
              (98.11570581159049, -45.18516408054211),
              (101.51034038803175, -31.804940398617475),
              (103.94217034284384, -19.427047474824803),
              (105.56391494229797, -7.638130175321521),
              (106.02313605731285, 3.305570023946302),
              (106.48235717232762, 14.249270223214012),
              (105.12910527762745, 24.457143644192058),
              (103.74213059466229, 34.65132630646025),
              (101.49425872051631, 44.758413505738474),
              (98.18508926516313, 54.758131085098796),
              (94.87591980981006, 64.75784866445912),
              (89.1847484586176, 75.2296467626748),
              (83.17291812445183, 85.76499512897482),
              (71.34393688820614, 99.51122751582983),
              (58.548078999534255, 108.91534794068599),
              (47.17347903940151, 114.19670888642742),
              (38.226671310064035, 115.55213697338178),
              (29.27986358072667, 116.90756506033614),
              (21.02696850984023, 116.12991211183186),
              (12.788547821925135, 115.30776504517058),
              (4.6130311445429015, 114.13639514186633),
              (-3.3927657195118854, 112.0227954166109),
              (-11.398562583566559, 109.90919569135559),
              (-19.370959871772016, 107.46506885288528),
              (-27.30770154792924, 104.66808883527898),
              (-35.24444322408635, 101.87110881767268),
              (-43.1666465887929, 97.9724586117498),
              (-51.0808178878907, 93.46516225994952),
              (-58.994989186988505, 88.95786590814902),
              (-67.15689198635289, 82.42493565115609),
              (-75.39826669727125, 75.24218492974586),
              (-83.6895104390062, 67.84905238792766),
              (-92.46515921562576, 58.412366735387366),
              (-101.24080799224532, 48.97568108284696),
              (-110.3989629408727, 38.290667267265405),
              (-119.75755908007568, 26.95150352799618),
              (-130.45563708246897, 12.324225231309015),
              (-143.51764282767238, -8.105942553783734)]
        self.templates.append(self.Template("Circle", t2))

        # points for triangle
        t3 = [(-147.8969777717473, 5.684341886080801e-13),
              (-142.16539006175287, 9.17184773103611),
              (-125.2190875354147, 12.827680591102308),
              (-109.4616067173688, 15.069066078145738),
              (-72.60100250736173, 26.890985707977165),
              (-55.55672879187887, 35.88668972298228),
              (-41.920107420857676, 44.221414365350256),
              (-29.504942054976937, 52.40179135523783),
              (-17.370720185273512, 60.546667296432474),
              (-4.532438457534454, 68.77249038747823),
              (8.731976318495072, 77.06081138385889),
              (23.19674518058241, 85.52554648316448),
              (34.84860378863664, 93.65155919907261),
              (45.245279200287314, 101.68597607626668),
              (54.54547153913609, 109.69119919801028),
              (67.63871242018809, 117.9596954805586),
              (97.33894477221816, 131.2165729515201),
              (93.38428472224746, 139.26626123975427),
              (86.68037579477641, 130.87104513680822),
              (84.90951193395813, 120.22040432402252),
              (82.99538645576877, 109.69189153258151),
              (81.03717752562375, 99.20035902011784),
              (79.16728994982714, 88.63599952170705),
              (77.78280077892782, 77.6266996827735),
              (76.90878938560445, 66.13332540684337),
              (77.11282489990526, 53.44190098082629),
              (77.43958195427786, 40.59867771928782),
              (77.05787847523311, 28.554169016695596),
              (76.12744950737056, 17.124421280813976),
              (74.61130698399552, 6.25387569324937),
              (73.08457760110718, -4.608012682616504),
              (70.67201510329937, -14.745527149873624),
              (68.2594526054911, -24.883041617130743),
              (65.56065479169797, -34.81895602594557),
              (62.71846570491789, -44.65387769417305),
              (59.847267656032955, -54.469585223660374),
              (56.91968034947104, -64.2479432259039),
              (54.00067477827042, -74.03197127099816),
              (51.13799234612566, -83.85321260670162),
              (48.457036862528184, -93.80466624610085),
              (46.317390119794936, -104.17165193520611),
              (43.58545427357103, -110.73373876024573),
              (34.99908795206329, -105.06468830981612),
              (26.0348326904666, -100.53358562402036),
              (17.070577428870138, -96.00248293822483),
              (7.774846690997265, -92.16319140254927),
              (-1.5572964343471085, -88.3998949176638),
              (-10.889439559691255, -84.6365984327781),
              (-20.306429517464267, -81.0274573754848),
              (-29.771201687673283, -77.50513025312023),
              (-39.2359738578823, -73.98280313075566),
              (-48.56132259954734, -70.19584214580948),
              (-57.7272856992206, -66.1063578437927),
              (-66.89324879889386, -62.016873541775794),
              (-75.77251196456587, -57.21022622796204),
              (-84.399655084384, -51.77291545742594),
              (-93.02679820420212, -46.335604686890065),
              (-101.57852336891233, -40.63019610168283),
              (-110.00521097033788, -34.48030055815627),
              (-118.43189857176344, -28.330405014629832),
              (-126.88369645431305, -22.277378136059497),
              (-135.38451516363125, -16.413460332798422),
              (-143.8853338729498, -10.549542529537462),
              (-152.66105522778196, -5.541905164155537)]
        self.templates.append(self.Template("Triangle", t3))

        Node.__init__(self, name, terminals=terminals)

    """
    Some functions (those with "_" / underscore before the name)
    are based on $1 recognizer
    """

    def register_buttons(self, buttons):
        """register callbacks for wiimote buttons to handle
        'A' for drawing gesture and
        'B' for recording template"""
        self.buttons = buttons
        self.buttons.register_callback(self.button_callback)

    def button_callback(self, buttons):
        """callback handles clicks on wiimote buttons"""
        if buttons:
            if buttons[0] == ('A', True):
                # clear recognized template from display
                self.recognizedTemplate = []
                self.aPressed = True
                # start recording gesture
                self.recordGesture()
            if buttons[0] == ('A', False):
                if self.aPressed:
                    # stop recording gesture
                    self.aPressed = False
                    # check template
                    template = self.checkRecognizedGesture(self.path)
                    # set label to display recognized template
                    name_score = template[0] + " | " + str(template[1])
                    self.label.setText("Recognized gesture: " + name_score)
                    # clear path
                    self.path = []

            if buttons[0] == ('B', True):
                # clear recognized template from display
                self.recognizedTemplate = []
                self.bPressed = True
                # start recording gesture
                self.recordGesture()
            if buttons[0] == ('B', False):
                if self.bPressed:
                    # stop recording gesture
                    self.bPressed = False
                    # set name for custom gesture with counter
                    name = self.TEMPLATE_NAME + str(self.templateCounter)
                    # add new template
                    self.addTemplate(name, self.path)
                    self.label.setText("Added Template: " + name)
                    self.templateCounter += 1
                    # clear path
                    self.path = []

    def setLabel(self, label):
        self.label = label
        self.label.setStyleSheet("font: 24pt; color:#33a;")

    class Template:
        """A gesture template. Used internally by Recognizer."""
        def __init__(self, name, points):
            """'name' is a label identifying this gesture,
            and 'points' is a list of tuple co-ordinates representing
            the gesture positions. Example: [(1, 10), (3, 8) ...]"""
            self.name = name
            self.points = points

    """
    Helper functions
    """
    def distance(self, x, y):
        # calculates distance between two points
        if x and y:
            dx = x[0] - y[0]
            dy = x[1] - y[1]
            distance = math.sqrt(abs(dx*dx - dy*dy))
            return distance

    def total_length(self, point_list):
        # sums up distances between a list of points
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
        if(len(points) >= 2):
            for point in points:
                x += point[0]
                y += point[1]
            x /= len(points)
            y /= len(points)
        return (x, y)

    def _rotateBy(self, points, theta):
        """Rotate a set of points by a given angle."""
        c = self._centroid(points)
        cos = math.cos(theta)
        sin = math.sin(theta)

        newpoints = []
        for point in points:
            qx = (point[0] - c[0]) * cos - (point[1] - c[1]) * sin + c[0]
            qy = (point[0] - c[0]) * sin + (point[1] - c[1]) * cos + c[1]
            newpoints.append((qx, qy))
        return newpoints

    def _boundingBox(self, points):
        """Returns a Rectangle representing the bounding box that
        contains the given set of points."""
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
        d = 0.0
        length = 0

        if len(pts1) > len(pts2):
            length = len(pts2)
        else:
            length = len(pts1)

        for index in range(length):
            d += self.distance(pts1[index], pts2[index])
        return d / len(pts1)

    def _distanceAtAngle(self, points, T, theta):
        """Returns the distance by which a set of points differs
        from a template when rotated by theta."""
        newpoints = self._rotateBy(points, theta)
        return self._pathDistance(newpoints, T.points)

    def _distanceAtBestAngle(self, points, T, a, b, threshold):
        """Search for the best match between a set of points and
        a template, using a set of tolerances. Returns a float
        representing this minimum distance."""
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

    def resample(self, point_list, step_count=64):
        """implements the resample function from protractor pseudo code
        of the $1 recognizer
        https://depts.washington.edu/aimgroup/proj/dollar/protractor.pdf"""
        newpoints = []
        length = self.total_length(point_list)
        stepsize = length/step_count
        curpos = 0
        newpoints.append(point_list[0])
        i = 1
        while i < len(point_list):
            p1 = point_list[i-1]
            d = self.distance(p1, point_list[i])
            cd = curpos + d
            s = stepsize
            if cd >= s and len(p1) >= 2 and len(point_list) >= 2 and d != 0:
                nx = p1[0] + ((s - curpos) / d) * (point_list[i][0] - p1[0])
                ny = p1[1] + ((s - curpos) / d) * (point_list[i][1] - p1[1])
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
        """Rotate a set of points such that the angle between the
        first point and the centre point is 0."""
        c = self._centroid(points)
        theta = math.atan2(c[1] - points[0][1], c[0] - points[0][0])
        return self._rotateBy(points, -theta)

    def _scaleToSquare(self, points, size):
        """Scale a scale of points to fit a given bounding box."""
        B = self._boundingBox(points)
        newpoints = []
        if(len(points) > 4):
            for point in points:
                qx = point[0] * (size / B[2])
                qy = point[1] * (size / B[3])
                newpoints.append((qx, qy))
        return newpoints

    def _translateToOrigin(self, points):
        """Translate a set of points, placing the centre point at the
        origin."""
        c = self._centroid(points)
        newpoints = []
        for point in points:
            qx = point[0] - c[0]
            qy = point[1] - c[1]
            newpoints.append((qx, qy))
        return newpoints

    # starting point for gesture recognition, after path is saved
    def checkRecognizedGesture(self, path):
        path = self.resample(path, len(path))
        path = self._rotateToZero(path)
        path = self._scaleToSquare(path, self.SQUARE_SIZE)
        path = self._translateToOrigin(path)

        bestDistance = float("infinity")
        bestTemplate = None
        if len(path) > 0:
            for template in self.templates:
                distance = self._distanceAtBestAngle(path,
                                                     template,
                                                     -self.ANGLE_RANGE,
                                                     +self.ANGLE_RANGE,
                                                     self.ANGLE_PRECISION)
                if distance < bestDistance:
                    bestDistance = distance
                    bestTemplate = template
                    self.recognizedTemplate = bestTemplate.points

            score = 1.0 - (bestDistance / self.HALF_DIAGONAL)
            # only show the last two (rounded) decimal points
            x = "{0:.2f}".format(round(score, 2))
            return (bestTemplate.name, x)
        else:
            return ("Path too short", "")

    # function to save gesture, while A-Button is pressed
    def recordGesture(self):
        self.path.append(self.inputVals)

    def addTemplate(self, name, points):
        """adds a recorded path to the list of templates
        path is prepared by passing through all steps of the
        $1 recognizer"""
        points = self.resample(points)
        points = self._rotateToZero(points)
        points = self._scaleToSquare(points, self.SQUARE_SIZE)
        points = self._translateToOrigin(points)
        self.templates.append(self.Template(name, points))

    def process(self, **kwds):
        if self.buttons is None:
            self.register_buttons(kwds['buttons'])

        self.inputVals = kwds['In']

        if self.aPressed or self.bPressed:
            # recording gesture while 'A' or 'B' is pressed
            self.label.setText("recording...")
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
    layout.setColumnStretch(0, 1)
    layout.setColumnStretch(1, 2)
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
    bn = fc.createNode('Buffer', pos=(150, 150))
    irn = fc.createNode('IrLightNode', pos=(300, 150))
    gn = fc.createNode('GestureNode', pos=(300, 300))
    gpn = fc.createNode('GesturePlotNode', pos=(450, 150))

    # connect ir camera
    plotter = view.addPlot()
    gpn.setPlot(plotter)

    # creating label for recognized gesture
    gestureLabel = QtGui.QLabel("please connect WiiMote")
    layout.addWidget(gestureLabel, 2, 0)
    gn.setLabel(gestureLabel)

    fc.connectTerminals(wiimoteNode['ir'], bn['dataIn'])
    fc.connectTerminals(wiimoteNode['buttons'], bn['buttons'])
    fc.connectTerminals(wiimoteNode['buttons'], gn['buttons'])
    fc.connectTerminals(bn['dataOut'], irn['In'])
    fc.connectTerminals(irn['Out'], gpn['positionIn'])
    fc.connectTerminals(irn['Out'], gn['In'])
    fc.connectTerminals(gn['pathOut'], gpn['pathIn'])
    fc.connectTerminals(gn['templateOut'], gpn['templateIn'])

    win.showMaximized()
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
