#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

class Setup():
    
    def __init__(self):
        self.array = []
        self.dict = {'k': 0.28, 'p': 1.1, 'b': 0.1, 'h': 0.4, 'm': 1.2}
    
    def readSetup(self):
        if len(sys.argv) > 1:
            with open(sys.argv[1]) as file:
                for line in file:
                    temp = line.split()
                    temp2 = temp[0].partition('#')[0]
                    #print(temp2)
                    temp3 = temp2.partition(' ')[0]
                    #print("temp3: ", temp3)
                    if(temp3 != ""):
                        self.array.append(temp3.lower())
                        #print("array: ",self.array)
                    
                    #TODO to lower
                    
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

def calculateDuration(setup, arr):
    if arr == "":
        return 0
    else:
        #for key, value in self.dict.items():
        return sum(setup.dict[k] for k in arr)
            #sum(B[k] for k in common)

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