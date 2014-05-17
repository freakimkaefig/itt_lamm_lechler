#!/usr/bin/python
# -*- coding: utf-8 -*-

#TODO:
#1) Texteingabe abfangen, abspeichern
#2) Stylesheet
#3) größenänderung visualisieren
#4) HTML abspeichern (formatierung!)

import sys
from PyQt4 import QtGui, QtCore
import re
from itertools import chain

class Painter(QtGui.QTextEdit):
    def __init__(self, parent=None):
        super(Painter, self).__init__(parent)

    def paintEvent(self, e):
        print "PAINTEVENT GOT CALLED"
        #self.startRect = QtCore.QRect(0, (self.height() / 2) - 50, 100, 100)
        #qp = QtGui.QPainter()
        #qp.begin(self)
        qp = QtGui.QPainter()
        #qp.setOpacity(0.5)
        qp.begin(self)
        self.drawCircle(qp)
        self.drawText(qp)
        qp.end()
        #qp.end()
            
    def drawText(self, qp):
        #print "DRAWTEXT GOT CALLED"
        qp.setPen(QtGui.QColor(0, 0, 0))
        qp.setFont(QtGui.QFont('Decorative', 32))
        st = SuperText(sys.argv[1])
        x = st.mouseX - 55
        y = st.mouseY + 16
        qp.drawText(x, y, "TEST")

    def drawCircle(self, qp):
        #print "DRAWCIRCLE GOT CALLED"
        #y = self.height() / 2
        #d = combination[0]
        #w = combination[1]
        #self.text = "Distance: " + str(d) + " | Width: " + str(w)
        st = SuperText(sys.argv[1])
        x = st.mouseX
        y = st.mouseY
        qp.setBrush(QtGui.QColor(0, 0, 255))
        self.center = QtCore.QPoint(x, y)
        #self.radius = w/2
        qp.drawEllipse(self.center, 80, 80)


class SuperText(QtGui.QTextEdit):

    def __init__(self, text):
        super(SuperText, self).__init__()
        self.textfile = text
        self.paragraphs = []    # list for paragraphs
        self.sizes = []         # list for font sizes
        self.readFile()         # read given textfile
        self.template = ""
        self.setHtml(text)
        self.generateTemplate()
        self.renderTemplate()
        self.initUI()
        self.textChanged.connect(self.onTextChanged)
        self.mouseX = 0
        self.mouseY = 0

    def initUI(self):
        self.setGeometry(0, 0, 640, 480)
        self.setWindowTitle('SuperText')
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)
        self.show()

    def wheelEvent(self, ev):
        #print "wheeeeeeeel"
        super(SuperText, self).wheelEvent(ev)
        self.generateTemplate()
        self.renderTemplate()
        self.mouseX = ev.x()
        self.mouseY = ev.y()
        anc = self.anchorAt(ev.pos())
        if (anc):
            self.changeSize(anc, ev.delta())
            painter = Painter(self)
            painter.paintEvent(ev)
        
    def onTextChanged(self):
        print "change"
        #print self.toPlainText()
        # save text

    def readFile(self):
        f = open(self.textfile, "r")
        data = f.read()
        # split textfile at linebreak
        self.paragraphs = data.split("\n")
        for i in range(len(self.paragraphs)):
            # set standard size for each paragraph
            self.sizes.append(14)
        #print self.paragraphs

    def generateTemplate(self):
        p = self.paragraphs
        content = "".join(str(i) for i in chain(*p))
        if len(p) == 0:
            self.template = p
            return
        for i in range(len(p)):
            size = str(self.sizes[i])
            content = re.sub(str(p[i]),
                             "<a href='%d'><p style='font-size:%spx'>$%d$</p></a>" % (i, size, i),
                             content, count=1)
        #print content
        self.template = content

    def renderTemplate(self):
        cur = self.textCursor()
        doc = self.template
        #print doc
        for i, paragraph in enumerate(self.paragraphs):
            doc = doc.replace('$' + str(i) + '$', '%s' % (paragraph))
        #print doc
        self.setHtml(doc)
        self.setTextCursor(cur)

    def changeSize(self, paragraphId, amount):      
        i = int(paragraphId)
        size = self.sizes[i]
        newSize = self.sizes[i] + (amount / 120)
        self.sizes[i] = newSize
        htmlCheck=self.toHtml()
        #print htmlCheck
        #self.setStyleSheet("QTextEdit a {background-color : #f00;}")
        self.generateTemplate()
        self.renderTemplate()


def main():
    if len(sys.argv) > 1:
        app = QtGui.QApplication(sys.argv)
        super_text = SuperText(sys.argv[1])
        sys.exit(app.exec_())
    else:
        print "Usage:"
        print "python demo.py <text.txt>"


if __name__ == '__main__':
    main()
