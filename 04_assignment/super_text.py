#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui, QtCore
import re

class SuperText(QtGui.QTextEdit):
 
    def __init__(self, example_text):
        super(SuperText, self).__init__()
        self.numbers=[]
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
            self.change_value(anc, ev.delta())

    def change_value(self, val_id, amount):
        self.numbers[int(str(val_id))] += amount / 120 
        self.render_template()
        
    def render_template(self):
        cur = self.textCursor()
        doc = self.template_doc 
        for num_id, num in enumerate(self.numbers):
            doc = doc.replace('$' + str(num_id) + '$', '%d' % (num))
        self.setHtml(doc)
        self.setTextCursor(cur)

    def generate_template(self):
        content = str(self.toPlainText())
        numbers = list(re.finditer(" -?[0-9]+", content))
        numbers = [int(n.group()) for n in numbers]
        self.numbers = numbers
        if len(numbers) == 0:
            self.template_doc = content
            return
        for num_id in range(len(numbers)):
            content = re.sub(" " + str(numbers[num_id])  , " <a href='%d'>$%d$</a>" % (num_id, num_id), content, count=1)
        self.template_doc = content

def main():
    app = QtGui.QApplication(sys.argv)
    super_text = SuperText("An 123 Tagen kamen 1342 Personen.")
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
