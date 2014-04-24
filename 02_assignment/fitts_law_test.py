#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui, QtCore
import logging
import csv
import random
import itertools
import time
from time import strftime


start = 0
end = 0
# time.time()


class Setup():

    def __init__(self):
        self.widths = []
        self.distances = []
        self.repetitions = 4
        self.combinations = []
        self.counter = -1

    def readSetupFile(self):
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
            self.combinations = self.calculateCombinations()
            return 1
        else:
            return 0

    def calculateCombinations(self):
        c = self.repetitions * list(itertools.product(self.distances, self.widths))
        random.shuffle(c)
        return c

    def getNextCombination(self):
        if self.counter < len(self.combinations):
            self.counter += 1
            return self.combinations[self.counter]


class ClickRecorder(QtGui.QWidget):

    def __init__(self, setup):
        super(ClickRecorder, self).__init__()
        self.setup = setup
        self.counter = 0
        self.initUI()
        self.mouseX = 150
        self.mouseY = 0
        self.active = 0

    def initUI(self):
        self.text = "Click the blue circles."
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setWindowTitle("Fitts' Law Test")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.show()

    def mousePressEvent(self, ev):
        if self.active == 0:
            # innerhalb startrechteck?
                #kreis zeichnen
                #startzeit setzen

            self.update()
            self.active = 1
        else:
            # innerhalb kreis?
            if((ev.x() - self.center.x())**2 + (ev.y() - self.center.y())**2 < self.radius**2):
                print("hit circle")
                #kreis löschen
                #endzeit setzen

            # entfernung zum mittelpunkt:
            xOffset = ev.x() - self.center.x()
            yOffset = ev.y() - self.center.y()
                #loggen (timestamp, width, distance, duration, xoffset, yoffset)
            print("xOffset: ", xOffset, " yOffset: ", yOffset)

            self.active = 0

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawStartPosition(event, qp)
        self.drawCircle(event, qp, self.setup.getNextCombination())
        self.drawText(event, qp)
        qp.end()

    def drawStartPosition(self, event, qp):
        qp.setBrush(QtGui.QColor(0, 0, 255))
        rect = QtCore.QRect(0, (self.height() / 2) - 50, 100, 100)
        qp.drawRect(rect)

    def drawText(self, event, qp):
        qp.setPen(QtGui.QColor(0, 0, 255))
        qp.setFont(QtGui.QFont('Decorative', 32))
        if self.counter > 0:
            self.text = str(self.counter)
        qp.drawText(150, 150, self.text)

    def drawCircle(self, event, qp, combination):
        y = self.height() / 2
        self.mouseY = y
        self.text = "Distance: " + str(combination[0]) + " | Width: " + str(combination[1])
        qp.setBrush(QtGui.QColor(0, 0, 255))
        self.center = QtCore.QPoint(self.mouseX + combination[0], y)
        self.radius = combination[1]/2
        qp.drawEllipse(self.center, self.radius, self.radius)

    def setStartTime():
        start = time.time()

    def setEndTime():
        end = time.time()

    def getDuration():
        return end - start

    def log(user, width, distance, timeInMs, offsetX, offsetY):
        logfile = open("user" + str(user) + ".csv", "w+")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        d = {"timestamp": timestamp, "user": user, "width": width, "distance": distance, "time(ms)": timeInMs, "offsetX": offsetX, "offsetY": offsetY}
        out = csv.DictWriter(logfile, ["timestamp", "user", "width", "distance", "time(ms)", "offsetX", "offsetY"])
        out.writeheader()
        out.writerow(d)
        logfile.close()


def initSetup():
    # creates new object of type setup
    # reads setup from given file
    setup = Setup()
    success = setup.readSetupFile()
    if success == 1:
        return setup
    else:
        return 0


def main():
    # prints secs since the epoch: print(time.time())

    setup_valid = initSetup()
    if setup_valid != 0:
        app = QtGui.QApplication(sys.argv)
        click = ClickRecorder(setup_valid)
        sys.exit(app.exec_())
    else:
        print "No setup file given"
        print "Usage: 'python space_counter.py <setup.txt>'"


if __name__ == '__main__':
    main()
