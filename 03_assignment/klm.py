#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import re

class Setup():
    
    def __init__(self):
        self.array = []
        self.dict = {'k': 0.28, 'p': 1.1, 'b': 0.1, 'h': 0.4, 'm': 1.2} #duration times according to Kieras (2011)
    
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
    
    
def predictKlm(array):
    executionTime = 0.0
    charArray = []
    for item in array:
        #print item
        line = re.findall('[0-9]*[a-z]', item)
        for charset in line:
            if len(charset) > 1:
                print charset
                factor = re.findall('[0-9]+', charset)
                char = re.findall('[a-z]', charset)
                for number in factor:
                    for i in range(int(number)):
                        charArray.append(char)
                #print factor
                #print char
            else:
                charArray.append(charset)
    print "ARRAY:"
    print charArray
        
    

def main():
    # prints secs since the epoch: print(time.time())

    setup_valid = initSetup()
    if setup_valid != 0:
        print("valid setup, do stuff!")
        predictKlm(setup_valid.array)
    else:
        print "No setup file given"
        print "Usage: 'python klm.py <setup.txt>'"


if __name__ == '__main__':
    main()