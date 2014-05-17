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

class Painter(QtGui.QWidget):
    def __init__(self, parent=None):
        super(Painter, self).__init__(parent)
        self.paintEvent()

    def paintEvent(self):
        print "PAINTEVENT GOT CALLED"
        #super(Painter, self).paintEvent(event)
        qp = QtGui.QPainter(self)#self.viewport())
        #qp.setOpacity(0.5)
        #qp.begin(self)
        self.drawCircle(qp)
        self.drawText(qp)
        #qp.end()
            
    def drawText(self, qp):
        #print "DRAWTEXT GOT CALLED"
        qp.setPen(QtGui.QColor(0, 0, 0))
        qp.setFont(QtGui.QFont('Decorative', 32))
        st = SuperText()
        x = st.mouseX - 55
        y = st.mouseY + 16
        #use st.sizes[] instead TEST
        qp.drawText(x, y, "TEST")

    def drawCircle(self, qp):
        #print "DRAWCIRCLE GOT CALLED"
        st = SuperText()
        x = st.mouseX
        y = st.mouseY
        qp.setBrush(QtGui.QColor(0, 0, 255))
        self.center = QtCore.QPoint(x, y)
        #self.radius = w/2
        qp.drawEllipse(self.center, 80, 80)


class SuperText(QtGui.QTextEdit):

    def __init__(self):
        super(SuperText, self).__init__()
        self.text = "New File"  # standard text
        self.paragraphs = []    # list for paragraphs
        self.sizes = []         # list for font sizes
        self.readText()         # read given textfile
        self.template = ""
        self.setHtml(self.text)
        self.setStyleSheet(".paragraph:hover { background:#f00; }")
        self.generateTemplate()
        self.renderTemplate()
        self.initUI()
        # connect onTextChange-Listener
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
            painter.update()
            #painter.paintEvent(ev)

    def onTextChanged(self):
        # update text when user inputs text
        self.text = self.toPlainText()
        self.readText()

    def readText(self):
        data = self.text
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
                             "<a class='paragraph' href='%d' style='color:#000; text-decoration:none;'><p style='font-size:%spx'>$%d$</p></a>" % (i, size, i),
                             content, count=1)
        #print content
        content = content + "<style>a:hover { background: #f00; }</style>"
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
        htmlCheck = self.toHtml()
        print htmlCheck
        #self.setStyleSheet("QTextEdit a {background-color : #f00;}")
        self.generateTemplate()
        self.renderTemplate()


def main():
    app = QtGui.QApplication(sys.argv)
    super_text = SuperText()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
