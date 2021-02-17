#!/usr/bin/env python3
#@ converts a CSV file to the RESULT log file required as input for 

import sys

with open(sys.argv[1]) as csvfile:
    header = [x.strip() for x in csvfile.readline().split(',')]
    for line in csvfile.readlines():
        csvlist = line.split(',')
        print("RESULT " + "\t".join(list(map(lambda x,y: (x + "=" + y), header, csvlist))))

