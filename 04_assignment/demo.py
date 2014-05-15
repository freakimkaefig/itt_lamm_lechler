#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui, QtCore
import re
from itertools import chain


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

    def initUI(self):
        self.setGeometry(0, 0, 400, 400)
        self.setWindowTitle('SuperText')
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)
        self.show()

    def wheelEvent(self, ev):
        super(SuperText, self).wheelEvent(ev)
        self.generateTemplate()
        self.renderTemplate()
        anc = self.anchorAt(ev.pos())
        if (anc):
            self.changeSize(anc, ev.delta())

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
        #print paragraphId
        #print amount
        #print self.paragraphs[int(paragraphId)]
        i = int(paragraphId)
        size = self.sizes[i]
        newSize = self.sizes[i] + (amount / 120)
        self.sizes[i] = newSize
        htmlCheck=self.toHtml()
        print htmlCheck
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
