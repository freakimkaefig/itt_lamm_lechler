#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import re


class Setup():

    def __init__(self):
        self.array = []
        self.dict = {'k': 0.28, 'p': 1.1, 'b': 0.1, 'h': 0.4, 'm': 1.2}
        # duration times according to Kieras (2011)

    def readSetup(self):
        if len(sys.argv) > 1:
            with open(sys.argv[1]) as file:
                for line in file:
                    temp = line.split()
                    temp2 = temp[0].partition('#')[0]
                    temp3 = temp2.partition(' ')[0]
                    if(temp3 != ""):
                        self.array.append(temp3.lower())
            return 1
        else:
            return 0


def calculateDuration(setup, arr):
    if arr == "":
        return 0
    else:
        return sum(setup.dict[k] for k in arr)


def initSetup():
    # creates new object of type setup
    # reads setup from given file
    setup = Setup()
    success = setup.readSetup()
    if success == 1:
        return setup
    else:
        return 0


def predictKlm(setup):
    charArray = []
    for item in setup.array:
        #print item
        line = re.findall('[0-9]*[a-z]', item)
        for charset in line:
            if len(charset) > 1:
                factor = re.findall('[0-9]+', charset)
                char = re.findall('[a-z]', charset)
                for character in char:
                    for number in factor:
                        for i in range(int(number)):
                            charArray.append(character)
            else:
                charArray.append(charset)

    executionTime = calculateDuration(setup, charArray)
    print "Predicted execution time:", executionTime


def main():
    # prints secs since the epoch: print(time.time())

    setup_valid = initSetup()
    if setup_valid != 0:
        predictKlm(setup_valid)
    else:
        print "No setup file given"
        print "Usage: 'python klm.py <setup.txt>'"


if __name__ == '__main__':
    main()
