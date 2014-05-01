#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

class Setup():
    
    def readSetup(self):
        if len(sys.argv) > 1:
            with open(sys.argv[1]) as file:
                for line in file:
                    temp = line.split()
                    #if temp[0] == "USER:":
                        #self.user = int(temp[1])
    
                    #if temp[0] == "WIDTHS:":
                        #for x in temp[1].split(','):
                            #self.widths.append(int(x))
    
                    #if temp[0] == "DISTANCES:":
                        #for x in temp[1].split(','):
                            #self.distances.append(int(x))
            #self.combinations = self.calculateCombinations()
            return 1
        else:
            return 0
        
def initSetup():
    # creates new object of type setup
    # reads setup from given file
    setup = Setup()
    success = setup.readSetup()
    if success == 1:
        return setup
    else:
        return 0


def main():
    # prints secs since the epoch: print(time.time())

    setup_valid = initSetup()
    if setup_valid != 0:
        print("valid setup, do stuff!")
        #app = QtGui.QApplication(sys.argv)
        #click = ClickRecorder(setup_valid)
        #sys.exit(app.exec_())
    else:
        print "No setup file given"
        print "Usage: 'python klm.py <setup.txt>'"


if __name__ == '__main__':
    main()