#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui, QtCore
import csv
import random
import itertools
import time
from time import strftime


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
        d = self.distances
        w = self.widths
        c = self.repetitions * list(itertools.product(d, w))
        random.shuffle(c)
        return c

    def getNextCombination(self):
        if (self.counter + 1) < len(self.combinations):
            self.counter += 1
            return self.combinations[self.counter]
        else:
            sys.exit()


class ClickRecorder(QtGui.QWidget):

    def __init__(self, setup):
        super(ClickRecorder, self).__init__()
        self.setup = setup
        self.initUI()
        self.logInit = 0
        self.mouseX = 0
        self.mouseY = 0
        self.active = 0
        self.misses = 0

    def initUI(self):
        self.clicked = 0
        self.text = "Click the blue circles."
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setWindowTitle("Fitts' Law Test")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.show()

    def mousePressEvent(self, event):
        self.clicked = 1
        self.mouseX = event.x()
        self.mouseY = event.y()
        self.update()

    def paintEvent(self, event):
        self.startRect = QtCore.QRect(0, (self.height() / 2) - 50, 100, 100)
        qp = QtGui.QPainter()
        qp.begin(self)

        mX = self.mouseX
        mY = self.mouseY

        if(self.clicked == 1):
            if self.active == 0:
                # innerhalb startrechteck?
                if(mX <= 100):
                    if(mY - self.startRect.y() <= 100):
                        if(mY - self.startRect.y() >= 0):
                            # kreis zeichnen
                            self.combination = self.setup.getNextCombination()
                            self.mouseXRect = mX

                            #startzeit setzen
                            self.setStartTime()

                            #self.update()
                            self.active = 1

            elif self.active == 1:
                # innerhalb kreis?
                cX = self.center.x()
                cY = self.center.y()
                if((mX - cX)**2 + (mY - cY)**2 < self.radius**2):
                    #endzeit setzen
                    self.setEndTime()
                    # entfernung zum mittelpunkt:
                    xOffset = mX - cX
                    yOffset = mY - cY
                    #log data
                    self.log(self.setup.user, self.combination[1],
                             self.combination[0], self.getDuration(),
                             xOffset, yOffset, self.misses)
                    self.active = 0
                    self.misses = 0
                else:
                    self.misses += 1

            self.clicked = 0
        if(self.active == 1):
            self.drawCircle(event, qp, self.combination)
            self.text = "click blue circle"
        else:
            self.text = "click blue rectangle"
        self.drawStartPosition(qp)
        self.drawText(qp)
        qp.end()

    def drawStartPosition(self, qp):
        qp.setBrush(QtGui.QColor(0, 0, 255))
        qp.drawRect(self.startRect)

    def drawText(self, qp):
        qp.setPen(QtGui.QColor(0, 0, 255))
        qp.setFont(QtGui.QFont('Decorative', 32))
        qp.drawText(150, 150, self.text)

    def drawCircle(self, event, qp, combination):
        y = self.height() / 2
        d = combination[0]
        w = combination[1]
        self.text = "Distance: " + str(d) + " | Width: " + str(w)
        qp.setBrush(QtGui.QColor(0, 0, 255))
        self.center = QtCore.QPoint(self.mouseXRect + d, y)
        self.radius = w/2
        qp.drawEllipse(self.center, self.radius, self.radius)

    def setStartTime(self):
        self.start = int(round(time.time() * 1000))

    def setEndTime(self):
        self.end = int(round(time.time() * 1000))

    def getDuration(self):
        return self.end - self.start

    def log(self, user, width, distance, timeInMs, offsetX, offsetY, misses):
        logfile = open("user" + str(user) + ".csv", "a")
        out = csv.DictWriter(logfile, ["timestamp", "user", "width",
                                       "distance", "time(ms)", "offsetX",
                                       "offsetY", "misses"])
        if self.logInit == 0:
            out.writeheader()
            self.logInit = 1

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        d = {"timestamp": timestamp, "user": user, "width": width,
             "distance": distance, "time(ms)": timeInMs, "offsetX": offsetX,
             "offsetY": offsetY, "misses": misses}
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
        print "Usage: 'python fitts_law_test.py <setup.txt>'"


if __name__ == '__main__':
    main()
