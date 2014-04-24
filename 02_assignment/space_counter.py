#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui, QtCore
import logging
import csv
import random
import itertools
import time


class Setup():

    widths = []
    distances = []
    repetitions = 4
    combinations = []
    counter = -1

    def __init__(self):
        self.read_setup_file()

    def read_setup_file(self):
        if len(sys.argv) > 1:
            with open(sys.argv[1]) as file:
                for line in file:
                    temp = line.split()
                    if temp[0] == "USER:":
                        self.user = int(temp[1])

                    if temp[0] == "WIDTHS:":
                        for x in temp[1].split(','):
                            self.widths.append(int(x))

                    if temp[0] == "DISTANCES:":
                        for x in temp[1].split(','):
                            self.distances.append(int(x))


class ClickRecorder(QtGui.QWidget):

    def __init__(self):
        super(ClickRecorder, self).__init__()
        self.counter = 0
        self.initUI()

    def initUI(self):
        self.text = "Please press 'space' repeatedly."
        self.setGeometry(300, 300, 280, 170)
        self.setWindowTitle('ClickRecorder')
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.show()

    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_Space:
            self.counter += 1
            self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawText(event, qp)
        self.drawRect(event, qp)
        qp.end()

    def drawText(self, event, qp):
        qp.setPen(QtGui.QColor(168, 34, 3))
        qp.setFont(QtGui.QFont('Decorative', 32))
        if self.counter > 0:
            self.text = str(self.counter)
        qp.drawText(event.rect(), QtCore.Qt.AlignCenter, self.text)

    def drawRect(self, event, qp):
        if (self.counter % 2) == 0:
            rect = QtCore.QRect(10, 10, 30, 30)
            qp.setBrush(QtGui.QColor(34, 34, 200))
        else:
            rect = QtCore.QRect(40, 10, 30, 30)
            qp.setBrush(QtGui.QColor(200, 34, 34))
        qp.drawRoundRect(rect)


def initLogging():
    log = logging.getLogger('space_counter')
    log.setLevel(logging.DEBUG)
    # file handler
    fh = logging.FileHandler('log.csv')
    fh.setLevel(logging.DEBUG)
    # console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    # set logging format

    #asctime liefert zeitstempel: [YYYY-MM-DD HH:MM:SS,MS]
    #das Komma am ende vor MS bewirkt spaltenwechsel in csv-datei

    format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add to handlers
    fh.setFormatter(format)
    ch.setFormatter(format)
    # add handlers to log
    log.addHandler(fh)
    log.addHandler(ch)
    # initial log
    log.info('Initial Log')


def init_setup():
    # creates new object of type setup
    # reads setup from given file
    setup = Setup()
    print "User: " + str(setup.user)


def log(user, width, distance, time):
    logfile = open("user" + str(user) + ".csv", "w+")
    d = {"timestamp": "%s\t%s\n % time.time()", "user": user, "width": width, "distance": distance, "time(ms)": time}
    out = csv.DictWriter(logfile, ["timestamp", "user", "width", "distance", "time(ms)"])
    out.writeheader()
    out.writerow(d)
    logfile.close()


def main():
    # prints secs since the epoch: print(time.time())
    # initLogging()
    log(1,50, 300, 222)
    init_setup()
    app = QtGui.QApplication(sys.argv)
    click = ClickRecorder()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
