#!/usr/bin/python
# -*- coding: utf-8 -*-

#TODO:
#1) Texteingabe abfangen, abspeichern
#2) Stylesheet
#4) HTML abspeichern (formatierung!)

import sys
from PyQt4 import QtGui, QtCore
import re
from itertools import chain
from threading import Timer


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
        self.size = ""
        self.active = 0

    def initUI(self):
        self.setGeometry(0, 0, 640, 480)
        self.setWindowTitle('SuperText')
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)
        self.show()

    def wheelEvent(self, ev):
        self.generateTemplate()
        self.renderTemplate()
        self.mouseX = ev.x()
        self.mouseY = ev.y()
        anc = self.anchorAt(ev.pos())
        self.paragraph = anc
        if (anc):
            self.changeSize(anc, ev.delta())
            self.active = 1
            self.update()

    def paintEvent(self, event):
        if(self.active == 1):
            qp = QtGui.QPainter()
            qp.begin(self.viewport())
            self.drawCircle(qp)
            self.drawText(qp, event)
            qp.end()
            t = Timer(1.0, self.changeActive)
            t.start()
        super(SuperText, self).paintEvent(event)

    def changeActive(self):
        if(self.active == 0):
            self.active = 1
        if(self.active == 1):
            self.active = 0
        self.update()

    def drawText(self, qp, ev):
        qp.setPen(QtGui.QColor(255, 255, 255))
        qp.setFont(QtGui.QFont('Decorative', 32))
        x = 550  # oder x = self.mouseX + 70
        y = 75  # oder y = self.mouseY - 20
        qp.drawText(x, y, str(self.sizes[int(self.paragraph)]))

    def drawCircle(self, qp):
        x = 575  # oder x = self.mouseX
        y = 60  # oder y = self.mouseY
        qp.setBrush(QtGui.QColor(0, 0, 255))
        self.center = QtCore.QPoint(x, y)
        qp.drawEllipse(self.center, 60, 60)

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
            self.sizes.append(18)
        #print self.paragraphs

    def generateTemplate(self):
        p = self.paragraphs
        content = "".join(str(i) for i in chain(*p))
        if len(p) == 0:
            self.template = p
            return
        for i in range(len(p)):
            self.size = str(self.sizes[i])
            content = re.sub(str(p[i]),
                             "<a class='paragraph' href='%d' style='color:#000; text-decoration:none;'><p style='font-size:%spx'>$%d$</p></a>" % (i, self.size, i),
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
