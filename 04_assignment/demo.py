#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui, QtCore
import re

class SuperText(QtGui.QTextEdit):
 
    def __init__(self, example_text):
        super(SuperText, self).__init__()
        self.words=[]
        self.template_doc = ""
        self.setHtml(example_text)
        self.prev_content = ""
        self.generate_template()
        self.render_template()
        self.initUI()
        
    def initUI(self):      
        self.setGeometry(0, 0, 400, 400)
        self.setWindowTitle('SuperText')
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)
        self.show()

    def wheelEvent(self, ev):
        super(SuperText, self).wheelEvent(ev)
        self.generate_template()
        self.render_template()
        anc = self.anchorAt(ev.pos())
        if (anc):
            self.change_size(anc, ev.delta())

    def change_value(self, val_id, amount):
        self.words[int(str(val_id))] += amount / 120 
        self.render_template()
        
    def render_template(self):
        cur = self.textCursor()
        doc = self.template_doc 
        for i, word in enumerate(self.words):
            doc = doc.replace('$' + str(i) + '$', '%s' % (word))
            #print word
        self.setHtml(doc)
        self.setTextCursor(cur)

    def generate_template(self):
        content = str(self.toPlainText())
        words = content.split()
        print words
        self.words = words
    
        if len(words) == 0:
            self.template_doc = content
            return
        for i in range(len(words)):
            content = re.sub(" " + str(words[i])  , " <a href='%d'>$%d$</a>" % (i, i), content, count=1)
        self.template_doc = content

def main():
    app = QtGui.QApplication(sys.argv)
    super_text = SuperText("An 123 Tagen kamen 1342 Personen.")
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
