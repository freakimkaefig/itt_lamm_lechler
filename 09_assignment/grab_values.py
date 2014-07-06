#!/usr/bin/env python
# coding: utf-8

import wiimote
import time
import sys
import csv

wm = wiimote.connect(sys.argv[1])

xp = yp = zp = 0
iteration = 0
logInit = 1 # set to '0' to write column headers        
onceA = 0


while True:
    if wm.buttons["A"]:
        onceA = 0
        x,y,z = wm.accelerometer
        if (x != xp) or (y != yp) or (z != zp):
            print("%d,%d,%d") % (x,y,z)
        xp,yp,zp = x,y,z
        
        logfile = open("trainingdata/"+str(iteration)+"data.csv", "a")
        out = csv.DictWriter(logfile, ["Iteration", "X", "Y", "Z"])
        if logInit == 0:
            out.writeheader()
            logInit = 1

        #d = {"Iteration": iteration, "X": xp, "Y": yp, "Z": zp} #uncomment to add iteration as first column
        d = {"X": xp, "Y": yp, "Z": zp}
        out.writerow(d)
        logfile.close()
        
        time.sleep(0.01)

    if wm.buttons["B"]:
        if(onceA == 0):
            onceA = 1
            print"new csv created"
            iteration += 1
            #logInit = 0 # uncomment to write column headers for any logfile

        
wm.disconnect()
time.sleep(1)
